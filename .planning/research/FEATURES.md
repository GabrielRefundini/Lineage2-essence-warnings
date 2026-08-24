# Feature Research

**Domain:** Screen-scanning event monitor + push alerting (game party watchdog → WhatsApp)
**Researched:** 2026-08-24
**Confidence:** MEDIUM

Adjacent domains surveyed, because no direct competitor exists for "L2 party monitor → WhatsApp":

1. **MMO death-alert addons** (WoW Death Alerts, DeathAlert, Deathlog, WeakAuras) — define what a *death alert* must contain.
2. **AFK watchdogs / game-event forwarders** (AFK Guard for WoW, ED-AFK-Notifier for Elite Dangerous, Telegram watchdog bots) — define the *game → messenger* pipeline shape.
3. **Infrastructure alerting** (Nagios/Icinga, Prometheus Alertmanager, Grafana Alerting, Uptime Kuma, Healthchecks.io) — define *false-positive suppression* and *observability*, which is where this project will actually live or die.
4. **Screen-scraping / RPA calibration UX** (UiPath clipping region, OpenCV `selectROI`, ROI Picker, screenshot overlay tools) — define *calibration UX*.

**The central insight from the survey:** in this domain the detection is the easy part and *trust* is the product. Every mature alerting tool spends the majority of its feature surface on not-crying-wolf (debounce, hysteresis, no-data state, dedup, cooldown) and on letting the user verify the thing works (test notification, status view, event history). A screen scanner that alerts correctly 90% of the time is worse than useless — the party mutes the WhatsApp group and the tool is dead. Budget accordingly.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Missing any of these and the tool gets turned off within one farming session.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Named events — "Kaus morreu", not "alguém morreu"** | Every WoW death addon (Death Alerts, DeathAlert, WeakAuras) leads with the player name + role. An anonymous alert is unactionable: the party can't decide whether to res, retreat, or ignore | MEDIUM | Requires OCR of party-window name column. Per PROJECT.md decision: OCR at startup + on composition change only, not per frame. Name is cached per row index |
| **Death detection with N-consecutive-frame confirmation (debounce)** | This is Nagios `max_check_attempts` verbatim — a non-OK check enters SOFT state and only notifies after re-checks confirm HARD state, explicitly "to prevent false alarms from transient problems". Grafana calls it *pending period* | MEDIUM | At ~1 Hz capture, 3 consecutive frames ≈ 3s to alert. Tunable in config, because the operational fix for false alarms in every one of these systems is "raise the retry count" |
| **Left-party detection, disambiguated from "UI gone"** | The single most likely false positive. "Row disappeared" is ambiguous between *left the party*, *alt-tabbed*, *loading screen*, and *party window moved* | MEDIUM | PROJECT.md's MP-bar-as-presence-check is the right primitive. Needs a window-level anchor check *above* the row-level check |
| **"Blind mode" / no-data state — suppress all alerts when the party window is not visible** | Grafana models this as a first-class **No Data** state, separate from Alerting, with its own handling policy and a "missing series evaluations to resolve" staleness counter. Alertmanager models the same idea as **inhibition**: when the root-cause alert (UI absent) is firing, suppress every symptom alert (per-member death/left) | MEDIUM | This is an *inhibition rule*, not a filter. State machine must have an explicit BLIND state that gates the dispatcher. Per PROJECT.md, BLIND is console-only in v1 — no WhatsApp alert |
| **Cooldown — exactly one alert per event instance** | Alert fatigue is the #1 documented killer of monitoring tools. A dead member stays dead for 30–120s; at 1 Hz that is 120 identical alerts without a cooldown | LOW | Edge-triggered state machine (alive→dead fires once) rather than level-triggered polling. Cooldown is the belt-and-braces on top |
| **Reliable delivery to Chatwoot with retry + visible failure** | An alerting tool that silently drops alerts is actively harmful — the party *believes* silence means everyone is alive. Every monitoring stack treats notification-delivery failure as its own alertable condition | LOW | Retry with exponential backoff + jitter; on final failure, print a loud console error. Never fail silently, never crash the capture loop on a network error |
| **Test alert / "send test notification"** | Universal across the category — Datadog has a *Test Notifications* button, Uptime Kuma and Healthchecks.io both have per-channel *Send test notification*, Grafana has *Send alert/check notification*. Users will not trust an alerting tool they cannot verify end-to-end before going AFK | LOW | `--test-alert` flag that POSTs a `[TESTE]` message to Chatwoot and exits. Should be step 1 of the user's first-run ritual |
| **Live console status while running** | The tool runs unattended for hours. The user needs a glance-check before walking away: capture rate, current roster, per-member HP%, current state, alerts sent, last Chatwoot response | LOW | Single repainting status block (not a scrolling log). This *is* the UI in v1 — treat it as such |
| **Region calibration a non-programmer can do** | The whole product is coordinate-dependent. If recalibration means editing pixel numbers in a file, the first time the window moves the tool is abandoned | MEDIUM | `cv2.selectROI` returns `[x, y, w, h]` from a drag-select in ~15 lines and is the standard Python answer. Persist to JSON (the ROI Picker pattern). A `--calibrate` subcommand |
| **Config persisted across restarts** | v1 is manually launched every farming session. Re-calibrating each launch is a non-starter | LOW | Single JSON/TOML file: ROIs, HSV thresholds, debounce counts, Chatwoot credentials, roster |
| **Clean start/stop** | Ctrl+C must exit cleanly and release the capture device; DXGI/dxcam handles left open are a real Windows failure mode | LOW | Signal handler + context-managed capture |
| **Secrets out of source** | Chatwoot API token must not live in a committed file | LOW | `.env` / OS env var, `.gitignore`d config |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Screenshot evidence attached to the alert** | Nothing in the game-alert space does this, and it is the single highest-leverage trust feature available. A cropped party-window image at the moment of detection makes every alert self-verifying and every false positive self-diagnosing. Change-monitoring tools (Visualping) and cloud monitoring both converged on "screenshot as evidence" for exactly this reason | MEDIUM | Ring buffer of the last N frames; on a confirmed event, attach the crop that triggered it. Chatwoot's API supports attachments. Also solves debugging: the user forwards the image instead of describing the bug |
| **Recovery alert (resurrection) with downtime duration** | `send_resolved` is opt-in-but-universal in Alertmanager, and Grafana models a **Recovering** state explicitly. The failure alert without the recovery alert leaves the group in permanent suspense — someone has to ask "voltou?". "Kaus ressuscitou (esteve morto 47s)" closes the loop and doubles as a quality signal for the detector | LOW | Free once the death state machine exists — it is the same edge, inverted. **Apply hysteresis:** require *more* confirmation frames to declare resurrection than to declare death, because HP flickering up for one frame is common. Different thresholds for entering vs exiting is the textbook hysteresis pattern |
| **MP-bar presence check as the three-way discriminator** | The core technical differentiator. Naive HP-only detection cannot tell *dead* from *left* from *UI hidden* and therefore cannot be trusted. MP present + HP empty = real death; MP absent but window anchor present = left party; anchor absent = blind | MEDIUM | Already the key decision in PROJECT.md. Worth calling out that this single primitive is what makes the whole product viable |
| **Auto re-anchor via template matching** | Removes the recalibration tax entirely. Match a stable party-window glyph (border corner, class icon frame) each run and derive all ROIs as offsets from it, so a moved window self-heals instead of producing garbage | MEDIUM | `cv2.matchTemplate` with a confidence floor; fall back to the saved absolute ROI, and to a loud "não achei a party window" console warning, if the match score is low. Directly addresses the "least painful re-calibration" question: the least painful recalibration is the one that doesn't happen |
| **Frame recorder + offline replay harness** | The developer/user cannot iterate on detection thresholds while simultaneously playing the game. Recording frames at state transitions and replaying them offline turns tuning from a live-fire exercise into a deterministic test loop, and turns every real false positive into a permanent regression fixture | MEDIUM | `--record` writes PNG + state JSON on every transition; `--replay <dir>` runs the detector over saved frames with no capture and no Chatwoot POST. Highest-value feature for long-term maintainability, invisible to the end user |
| **Dry-run mode (detect + log, never send)** | Lets the user run a full farming session with the detector live and no risk of spamming the group, then review the event log to decide whether to trust it. The onboarding ramp: `--test-alert` → `--dry-run` session → live | LOW | One boolean at the dispatcher boundary. Console prints "[DRY-RUN] enviaria: ..." |
| **Self-monitoring (own character's HP bar)** | The user's own death is the event *they* most need broadcast, and the party window typically does not show the player's own row. Every AFK-watchdog analog (ED-AFK-Notifier on hull damage, AFK Guard on killed-by-player) exists precisely for the AFK operator's own character | LOW | Separate ROI at the top-of-screen HP bar; reuses the same bar-reading and state machine code. Already an Active requirement in PROJECT.md |
| **Structured event log (JSONL) + session summary on exit** | Post-farm forensics: "quantas vezes o Korzis morreu hoje", "o alerta das 21h32 foi falso positivo?". Every monitoring tool ships history; Uptime Kuma's charts are a headline feature | LOW | Append-only JSONL with timestamp, member, event, confidence, screenshot path. Ctrl+C prints a per-member death/leave tally |
| **Heartbeat / staleness self-check** | Healthchecks.io's whole product is "absence of signal is itself an alert". If the capture loop stalls or the game closes, the party's silence is indistinguishable from everyone-is-fine | LOW-MEDIUM | v1: watchdog detects a stalled loop and screams on the console. v2: periodic heartbeat so the party can tell "scanner rodando" from "scanner morto". Keep off WhatsApp in v1 per the PROJECT.md decision on loss-of-vision alerts |
| **Per-event message templates** | Death, left, and resurrection deserve different tone and urgency; templated strings let the user tune copy without touching detection code | LOW | Format strings in config: `"☠️ {nome} morreu"` / `"🚪 {nome} saiu da party"` / `"✨ {nome} ressuscitou (morto por {duracao})"` |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Any input injection / auto-res / auto-potion / macro** | "If it can see the death, why not just fix it?" | This is the ban vector, full stop. L2 anticheats (SmartGuard, L2s-Guard) advertise *explicit blocking of emulated mouse and keyboard input* as a headline feature. Passive screen capture uses the same DirectX path as OBS and Discord and touches no game process; synthetic input is the line that turns a monitor into a bot | Read-only, forever. The tool never sends a single event to the game. Make this an architectural invariant, not a policy — no input library in the dependency list at all |
| **Memory reading / packet sniffing / DLL injection** | "More reliable than pixels" | Already Out of Scope in PROJECT.md and correctly so. In-process access leaves forensic traces anticheats actively scan for; L2 traffic is encrypted by the guard specifically to defeat packet tooling. Both also break on every patch | Screen capture. It is patch-proof, ban-proof, and the data is right there |
| **Low-HP / "está morrendo!" warnings** | Feels more useful than death alerts — warn before it happens | Catastrophic spam. During normal farming HP oscillates across any threshold continuously; this generates dozens of alerts per minute and gets the WhatsApp group muted, which destroys the *real* alerts too | Only fire on confirmed 0-HP with debounce. If a "danger" signal is ever wanted, it belongs on the console, never on WhatsApp |
| **WhatsApp alert on loss of vision (blind mode)** | Symmetry — "shouldn't the party know the scanner went blind?" | Alt-tab, inventory screens, and loading are constant during farming. This would be the noisiest alert in the system by an order of magnitude. The user has already explicitly declined it | Console-only BLIND state in v1. If revisited, gate it behind a long threshold (blind > 5 min) so it fires once per genuinely-gone session |
| **Uploading screenshots to a third-party image host (imgur/S3) to get a URL** | Easiest way to attach an image to a message | Sends the user's game screen — including chat, character names, and whatever else is on screen — to an unrelated third party. The user already self-hosts Chatwoot precisely to keep this in their own infrastructure | Attach the image directly to the Chatwoot API request, or keep evidence local and reference it by filename in the message |
| **Continuous OCR of names every frame** | "Then it always knows who's who, even if rows reorder" | Tesseract on a stylized game font at 1 Hz × N rows is both the CPU hot spot and the flakiest component. Transient misreads would produce phantom "X saiu / Y entrou" churn — turning the most expensive feature into the largest false-positive source | Already decided: OCR at startup and on composition change only. Between OCR passes, track members by row index + bar geometry |
| **Autostart with Windows / always-on service** | "I'll forget to start it" | A scanner running when the user is not farming watches whatever happens to be on screen and produces confusing or spurious alerts; it also makes "is it running?" ambiguous. Already deferred to v2 in PROJECT.md | Manual launch in v1. If revisited, gate on game-process-detected rather than on boot |
| **Graphical overlay drawn on top of the game** | "Prettier than a console" | An overlay over a DirectX game means either a transparent always-on-top window fighting the game's exclusive/fullscreen behavior, or hooking the renderer — the latter is squarely in ban territory. It also adds zero value: the operator is AFK and the alerts go to a phone | Console status block. A separate non-overlay window is acceptable later if a GUI is truly wanted |
| **Two-way WhatsApp commands ("!status", "!pause")** | "Control it from my phone" | Turns a one-way outbound POST into a bot requiring an inbound Chatwoot webhook, a publicly reachable endpoint on the gaming PC, and command authorization. Massive surface expansion for marginal gain | One-way outbound only. Status lives on the console, on the machine the user is sitting at |
| **Sound / TTS alerts on the local machine** | Cheap to add | The premise of the product is that the operator is AFK and away from the machine. Local sound reaches nobody | WhatsApp is the channel. A local beep is at most a debugging aid |
| **Generic "works with any game / any UI" abstraction** | Reusability | Premature generalization of a detector that does not yet work once. The HSV thresholds, bar geometry, and MP-presence trick are all L2-Essence-specific | Hardcode L2 Essence. Keep ROIs and thresholds in config so a second layout is *possible*, but do not build the plugin system |
| **Alerting on non-party entities (mobs, enemy players, raid bosses)** | Scope creep from "it's watching the screen anyway" | Different detection problem entirely, and every added alert type dilutes the signal of the ones that matter | Party members only. Ship, validate, then reconsider |
| **Alert grouping/batching (Alertmanager `group_wait`)** | Standard practice in infra alerting — collapse a storm into one notification | Deliberately *not* applicable here. Alertmanager's own docs note group_wait trades latency for consolidation, and PROJECT.md requires seconds-level latency. A 4-person party will never produce a hundred-alert storm | Send immediately. Revisit only if wipe events (whole party dies at once) prove noisy — then batch a wipe into a single "PARTY WIPE" message |

---

## Feature Dependencies

```
[Screen capture loop]
    ├──requires──> [ROI calibration + persisted config]
    │                   └──enhanced by──> [Template-match auto-anchor]
    │
    ├──> [Window anchor presence check]
    │        └──produces──> [BLIND state] ──inhibits──> [ALL alert dispatch]
    │
    └──> [Per-row bar reading (HP + MP, HSV)]
             ├──> [MP presence check] ──discriminates──> [DEAD vs LEFT vs BLIND]
             │
             ├──> [Death detection] ──requires──> [Debounce: N consecutive frames]
             │        └──requires──> [Cooldown / edge-triggered state machine]
             │        └──enables──> [Resurrection detection]
             │                          └──requires──> [Hysteresis: higher N to exit DEAD]
             │
             └──> [Left-party detection] ──requires──> [Roster baseline]
                                                └──requires──> [OCR of names]

[Alert dispatch] ──requires──> [Chatwoot client]
     ├──requires──> [Retry + backoff]
     ├──gated by──> [Dry-run flag]
     ├──verified by──> [--test-alert]
     └──enhanced by──> [Screenshot evidence] ──requires──> [Frame ring buffer]

[Frame recorder] ──enables──> [Offline replay harness] ──enables──> [Threshold tuning + regression fixtures]

[Event log JSONL] ──enables──> [Session summary on exit]

[Self-character HP bar] ──reuses──> [Bar reading] + [Death state machine]

[Continuous OCR] ──conflicts──> [Low-CPU 1 Hz loop] + [Left-party stability]
[Alert grouping / group_wait] ──conflicts──> [Seconds-level latency requirement]
[Blind-mode WhatsApp alert] ──conflicts──> [Alert-fatigue avoidance]
```

### Dependency Notes

- **Everything requires ROI calibration.** It is the root of the tree and the highest-risk UX surface. It must be phase 1, and it must be drag-select, not hand-edited coordinates.
- **BLIND state inhibits all dispatch, and must be evaluated first.** This is Alertmanager's inhibition semantics: the root-cause condition suppresses the symptoms. If the window-level anchor check runs *after* per-row checks, an alt-tab produces four simultaneous "saiu da party" alerts. Order of evaluation is a correctness property, not an optimization.
- **Left-party detection requires the roster baseline from OCR**, which makes OCR a hard dependency of one of the two headline events. If OCR proves unreliable, the fallback is a manually configured roster in the config file — worth having as an escape hatch, since names in a fixed party rarely change.
- **Resurrection detection is nearly free once death detection exists**, but must not reuse the same threshold. Hysteresis (higher confirmation count to exit DEAD than to enter it) is what prevents a one-frame HP flicker from producing a "ressuscitou" followed immediately by a second "morreu" — the flapping pattern that `keep_firing_for` / Recovering states exist to prevent.
- **Screenshot evidence requires a frame ring buffer**, because by the time the debounce confirms (3+ frames later) the triggering frame is gone. Keep the frame that *started* the pending state, not the one that confirmed it — that is the more informative image.
- **The replay harness depends on the frame recorder and pays for both.** Any real-world false positive becomes a saved fixture; tuning stops being guesswork.
- **Continuous OCR conflicts with two things at once** (CPU budget and left-party stability), which is why the once-at-startup decision in PROJECT.md is load-bearing rather than an optimization.

---

## MVP Definition

### Launch With (v1)

- [ ] **ROI calibration via drag-select, persisted to config** — nothing works without it; hand-edited coordinates guarantee abandonment
- [ ] **Capture loop at ~1 Hz with HSV bar reading (HP + MP per row)** — the sensor
- [ ] **Window-anchor presence check → BLIND state that inhibits all dispatch** — without this the first alt-tab produces a false wipe alert and the tool loses all credibility
- [ ] **Death detection with N-consecutive-frame debounce** — the primary event
- [ ] **Left-party detection via MP-presence discriminator** — the secondary event; the discriminator is what makes it trustworthy
- [ ] **Name identification via OCR at startup + on composition change** — an anonymous alert is unactionable
- [ ] **Edge-triggered state machine + cooldown (one alert per event instance)** — spam kills the WhatsApp group
- [ ] **Chatwoot POST with retry, backoff, and loud console failure** — silent delivery failure is worse than no tool
- [ ] **`--test-alert`** — the user must be able to verify the pipeline before trusting it
- [ ] **`--dry-run`** — the user must be able to trial a full session without risking spam
- [ ] **Live console status block** — the pre-AFK glance-check
- [ ] **Own-character HP bar monitoring** — the user's own death is the one they most need broadcast

### Add After Validation (v1.x)

- [ ] **Resurrection alert with downtime duration** — add as soon as death detection has proven stable for a few sessions; needs hysteresis tuning that only real data provides
- [ ] **Screenshot evidence attached to alerts** — add once event timing is trusted; the ring buffer is trivial, the value is in trust-building and remote debugging
- [ ] **Frame recorder + offline replay harness** — add the moment the first false positive appears in the wild; that false positive becomes fixture #1
- [ ] **Template-match auto-anchor** — add when the user first has to recalibrate; before that it is speculative
- [ ] **Structured JSONL event log + session summary on exit** — add when the user starts asking "how many times did X die today"
- [ ] **Per-event message templates in config** — add when the user wants to change the copy

### Future Consideration (v2+)

- [ ] **Windows Graphics Capture for background-window capture** — already flagged in PROJECT.md; lets the game sit unfocused. Defer because it changes the capture backend and the current constraint (game visible) is acceptable
- [ ] **Autostart / game-process-triggered start** — defer per PROJECT.md; a scanner running outside farming sessions creates confusion
- [ ] **Chat-line OCR as a corroborating signal** — "X has left the party" exists in the system chat and could raise confidence on left-party events; defer because chat scrolls fast and OCR on it is a second, harder OCR problem
- [ ] **Heartbeat to WhatsApp ("scanner ainda rodando")** — defer; the console covers it while the user is at the machine, and it risks becoming noise
- [ ] **Wipe consolidation (whole party dies → one message)** — defer until wipe noise is actually observed
- [ ] **Per-member routing / muting** — defer until the party is larger than 4 or someone complains

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Death detection + debounce | HIGH | MEDIUM | P1 |
| BLIND state inhibiting dispatch | HIGH | MEDIUM | P1 |
| Left-party detection (MP discriminator) | HIGH | MEDIUM | P1 |
| Name identification (OCR at startup) | HIGH | MEDIUM | P1 |
| Cooldown / edge-triggered state machine | HIGH | LOW | P1 |
| Chatwoot delivery + retry + visible failure | HIGH | LOW | P1 |
| ROI calibration (drag-select + persist) | HIGH | MEDIUM | P1 |
| `--test-alert` | HIGH | LOW | P1 |
| `--dry-run` | HIGH | LOW | P1 |
| Live console status | HIGH | LOW | P1 |
| Own-character HP monitoring | HIGH | LOW | P1 |
| Resurrection alert + duration | MEDIUM | LOW | P2 |
| Screenshot evidence on alert | HIGH | MEDIUM | P2 |
| Frame recorder + replay harness | MEDIUM (HIGH for maintainer) | MEDIUM | P2 |
| Template-match auto-anchor | MEDIUM | MEDIUM | P2 |
| JSONL event log + session summary | MEDIUM | LOW | P2 |
| Message templates in config | LOW | LOW | P2 |
| Heartbeat / staleness self-check | MEDIUM | LOW | P2 |
| Windows Graphics Capture backend | MEDIUM | HIGH | P3 |
| Chat-line OCR corroboration | LOW | HIGH | P3 |
| Autostart | LOW | LOW | P3 |
| Wipe consolidation | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | WoW death addons (Death Alerts / DeathAlert / Deathlog) | AFK watchdogs (AFK Guard, ED-AFK-Notifier) | Infra alerting (Nagios / Alertmanager / Grafana / Uptime Kuma) | Our Approach |
|---------|---------------------------------------------------------|--------------------------------------------|---------------------------------------------------------------|--------------|
| **Event source** | In-game API (combat log) — exact, no false positives | Game journal file / addon events | Active probes + push heartbeats | Screen capture only — the sole legal/safe channel in L2, at the cost of owning the false-positive problem ourselves |
| **Who died** | Name + role + class, always | Character name | N/A (host/service name) | OCR name at startup, tracked by row index; manual roster fallback in config |
| **Cause of death** | Yes — Death Alerts reports cause and damage taken | Partial (hull damage source) | N/A | **Not attempted.** Not available from the party window; would require combat-log OCR. Explicitly out of scope |
| **Delivery channel** | In-client: chat line, on-screen text, role-specific sound | Discord / Telegram / phone push | Email, Slack, PagerDuty, webhooks | Chatwoot → WhatsApp; one-way outbound POST only |
| **False-positive handling** | Not needed — the API is authoritative | Minimal | The bulk of the feature surface: soft/hard states + `max_check_attempts`, pending period, hysteresis, flap detection, dedup, inhibition, No Data state | **Adopt the infra playbook wholesale.** This is where our engineering goes, because our sensor is the noisy one |
| **Recovery notification** | Implicit (combat log res event) | Rare | Standard — `send_resolved`, Grafana Recovering state | Resurrection alert with downtime duration, gated behind hysteresis |
| **Test / verify** | Reload UI and die | Manual | Universal "Send test notification" button (Datadog, Uptime Kuma, Healthchecks, Grafana) | `--test-alert` + `--dry-run` + `--replay` — three levels of verification, more than any analog offers |
| **Evidence** | None | None | Screenshot-as-evidence in change monitoring (Visualping) and cloud incident views | **Screenshot crop attached to every alert.** Our clearest differentiator, and mandatory given a probabilistic sensor |
| **Calibration** | None needed | None needed | None needed | Drag-select ROI → JSON → template-match re-anchor. Unique burden of the screen-scraping approach; minimizing it is a first-class product concern |
| **History** | Deathlog keeps a death log | Dashboards / character reports (AFK Guard) | Charts, event history (Uptime Kuma) | JSONL event log + session summary on exit |
| **Automation / response** | Some addons trigger macros | AFK Guard replies to whispers in-game | Event handlers, auto-remediation | **Deliberately none.** Read-only is the ban-risk invariant |

---

## Open Questions for Requirements

1. **Roster source of truth** — if OCR proves unreliable on the L2 Essence font, is a hand-configured roster in the config file an acceptable v1 fallback? (Party composition is stable in practice; this may be the *better* default.)
2. **Wipe semantics** — when all four members die within a few seconds, is that four alerts or one "PARTY WIPE"? Affects the dispatcher design; deferring is fine but the state machine should not preclude it.
3. **Chatwoot attachment support** — the screenshot-evidence feature assumes the configured Chatwoot→WhatsApp flow forwards media. Needs empirical confirmation before committing to it as a P2. (Text-only fallback: write the crop locally and reference the filename.)
4. **Death vs disconnect** — a disconnected member's row behavior in the party window is unverified. If a disconnect looks like a death, the alert copy should hedge ("morreu ou caiu").

---

## Sources

**Alerting patterns and false-positive suppression** (cross-corroborated across four independent systems → MEDIUM confidence):
- [Nagios Core — State Types (soft/hard, `max_check_attempts`)](https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/statetypes.html)
- [Nagios Core — Detection and Handling of State Flapping](https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/3/en/flapping.html)
- [Prometheus — Alertmanager (grouping, inhibition, silences)](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Grafana — Alert rule evaluation (pending period, keep firing for)](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/)
- [Grafana — No Data and Error states](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/nodata-and-error-states/)
- [Grafana — Alerting best practices](https://grafana.com/docs/grafana/latest/alerting/guides/best-practices/)
- [Webalert — Alert Flapping: Causes, Detection, and Fixes](https://web-alert.io/blog/alert-flapping-detection-taming-unstable-alerts)
- [incident.io — Alert fatigue solutions for DevOps teams](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works)

**Test / verification UX** (MEDIUM):
- [Datadog — Monitor Notifications (Test Notifications button)](https://docs.datadoghq.com/monitors/notify/)
- [Dash0 — Send alert/check notifications](https://www.dash0.com/docs/dash0/monitoring/alerting/send-alert-check-notifications)
- [OneUptime — Alert Testing Strategies](https://oneuptime.com/blog/post/2026-01-30-alert-testing-strategies/view)

**Heartbeat / dead-man's-switch monitoring** (LOW — comparison blogs, not primary docs):
- [Healthchecks.io — FAQ](https://healthchecks.io/faq/)
- [Uptime Kuma vs Healthchecks.io for Solo Self-Hosters](https://futurion.blog/self-hosting-uptime-kuma-vs-healthchecks-io-honest-trade-offs-for-solo-builders/)
- [Uptime Kuma vs Gatus vs Healthchecks](https://selfhostpicks.com/uptime-kuma-vs-gatus-vs-healthchecks/)

**Calibration UX / ROI selection** (MEDIUM):
- [LearnOpenCV — How To Select a Bounding Box (ROI) in OpenCV](https://learnopencv.com/how-to-select-a-bounding-box-roi-in-opencv-cpp-python/)
- [GeeksforGeeks — Python OpenCV `selectROI()`](https://www.geeksforgeeks.org/python/python-opencv-selectroi-function/)
- [mint-lab/roi_picker — JSON-persisted ROI editor](https://github.com/mint-lab/roi_picker)
- [UiPath Forum — Select Clipping Region (click and drag)](https://forum.uipath.com/t/select-clipping-region-click-and-drag/91452)
- [Alt Controller — Defining screen regions](https://altcontroller.net/docs/defining-screen-regions/)

**MMO death-alert prior art** (LOW — addon listing pages):
- [Death Alerts — CurseForge](https://www.curseforge.com/wow/addons/deathalerts)
- [DeathAlert — CurseForge](https://www.curseforge.com/wow/addons/deathalert)
- [Deathlog — CurseForge](https://www.curseforge.com/wow/addons/deathlog)
- [WeakAura — Raid/Party Member Death](https://www.mmo-champion.com/threads/1339540-Weak-Aura-Raid-Party-Member-Death)

**AFK watchdog / game→messenger pipelines** (LOW):
- [ED-AFK-Notifier — Elite Dangerous hull damage → Telegram](https://github.com/tommyblue/ED-AFK-Notifier)
- [AFK Guard — forwards in-game events to Discord/phone](https://www.ownedcore.com/forums/wow-classic/wow-classic-bots-programs/893272-afk-guard-alert-respond-game-whispers-channels-discord-free-beta.html)
- [telegram-watchdog-bot](https://github.com/idosekely/telegram-watchdog-bot/blob/master/watchdog.py)

**Screenshot as evidence** (LOW):
- [Visualping — Screenshots as Evidence](https://visualping.io/blog/screenshots-as-evidence)
- [Google Cloud Monitoring — Display incidents and charts for alerting policies](https://cloud.google.com/monitoring/dashboards/alerts-and-incidents)

**L2 anticheat / ban-risk surface** (LOW — vendor and bot-community sources, directionally corroborated but not neutral research):
- [SmartGuard — Lineage 2 Bot Protection (blocks emulated mouse/keyboard input)](https://smart-guard.eu/en)
- [L2s-Guard — Anticheat/antibot for Lineage 2 servers](https://guard.l2-scripts.com/)
- [Unbanster — Cheating in Video Games: Bans, Methods, Detection](https://unbanster.com/cheating-ban-games/)

---
*Feature research for: screen-scanning game party monitor with push alerting*
*Researched: 2026-08-24*
