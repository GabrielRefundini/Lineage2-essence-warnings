# Stack Research

**Domain:** Real-time screen-scanning desktop monitor (Windows 11) — party-UI state detection in Lineage 2 XM Essence → WhatsApp alerts via Chatwoot API
**Researched:** 2026-08-24
**Confidence:** MEDIUM-HIGH (versions verified against canonical PyPI/python.org endpoints; behavioural claims about Windows Graphics Capture and the Chatwoot/WhatsApp outbound path are MEDIUM and flagged for a spike)

> **Confidence convention used in this doc.** The GSD `classify-confidence` seam rates the providers available in this run (`webfetch`, `websearch`) as **LOW** generically. Where a fact was read directly from a canonical registry endpoint (`pypi.org/pypi/<pkg>/json`, `devguide.python.org/versions`, `developers.chatwoot.com`), it is labelled **HIGH (primary source)** because the seam's generic tier does not reflect reading the registry of record. Everything sourced from blog posts / forum threads / search summaries retains **LOW–MEDIUM** and is marked as such.

---

## TL;DR — The Prescriptive Answer

| Concern | Decision | One-line why |
|---|---|---|
| Runtime | **Python 3.13.x, 64-bit** | Every wheel we need exists; 3.14 is stable but wheel coverage for the OCR tail lags |
| (a) Screen capture | **`mss` 10.2.0** | 1–5 Hz needs ~2% of mss's throughput; pure-ctypes, zero binary deps, no `None`-on-unchanged-frame footgun |
| (a) Capture — fast path (opt-in) | **`dxcam` 0.3.0** behind a flag | Only if profiling proves mss is the bottleneck, or user switches to fullscreen-exclusive |
| (a) Capture — background window (v2) | **`windows-capture` 2.0.1** | Only WGC can plausibly see an *occluded* window; **must be spiked**, does not solve minimized |
| (b) Bar analysis | **`opencv-python>=4.14,<5`** + **`numpy` 2.5.2** | 4.14.0.94 is current and every recipe on earth targets 4.x; OpenCV 5.0 is 2 months old |
| (c) OCR | **Windows.Media.Ocr via `winrt-*` bindings** — primary; **`rapidocr` 3.9.2** — fallback | Zero system install is worth more than raw accuracy here; names are a *closed set* |
| (c) OCR robustness | **`rapidfuzz` 3.14.5** matched against a configured roster | You know your 4–8 party members. Fuzzy-match, don't free-read. |
| (d) Chatwoot | **`requests` 2.34.2** + `urllib3.Retry` | One idempotent POST with backoff; async buys nothing |
| Console UI | **`rich` 15.0.0** | `Live` + `Table` gives the real-time status board the requirement asks for |
| Config | **`config.toml` (human, stdlib `tomllib`) + `calibration.json` (machine, stdlib `json`)** | Zero deps both ways; calibrator never clobbers hand-written settings |
| Secrets | **`.env` + `python-dotenv` 1.2.3** | Chatwoot token must not live in a file the user might screenshot or share |
| Packaging | **`uv` 0.12.5 + a 2-line `run.bat`** | No venv activation ritual; no PyInstaller antivirus roulette |
| Validation | **`pydantic` 2.13.4** | Config typos should fail at startup with a readable message, not at 2am mid-farm |

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **CPython (64-bit)** | **3.13.x** | Runtime | `numpy` 2.5.2 requires `>=3.12`; `dxcam` 0.3.0 requires `>=3.10`; `rapidfuzz` and `requests` require `>=3.10`. 3.13 sits in the sweet spot where *every* candidate library ships a prebuilt wheel. 3.14 (stable since 2025‑10‑07) is a valid choice but the OCR tail (`rapidocr` → `onnxruntime`, `pytesseract`) is where 3.14 wheel gaps historically bite. **64-bit is mandatory** — several WinRT/DXGI bindings ship x64-only wheels. *(HIGH — primary source: devguide.python.org/versions, PyPI JSON)* |
| **`mss`** | **10.2.0** (2026‑04‑23) | Primary screen capture of the party-window region | Pure-Python ctypes wrapper over Win32 GDI. **Zero binary dependency, zero DLL to ship, near-zero failure modes.** Delivers 30–60 FPS on Windows — the requirement is **1 Hz**, so we are using ~2–3% of its capacity. Critically, `mss.grab(region)` **always returns pixels**; it has no "frame unchanged → return `None`" behaviour, which is a genuine footgun at low poll rates (see *What NOT to Use*). Region capture takes a plain dict `{"left","top","width","height"}` in **physical** pixels, which maps 1:1 onto our calibration file. *(version HIGH — PyPI JSON; perf claims MEDIUM — blog benchmarks)* |
| **`opencv-python`** | **`>=4.14,<5`** (latest 4.x: **4.14.0.94**, 2026‑07‑29) | HSV thresholding, bar-fill measurement, template matching, image upscaling for OCR | The 4.x line is **not** legacy — 4.14.0.94 shipped four weeks ago and OpenCV maintains 4.x and 5.x as parallel stable branches. Pin below 5 because OpenCV 5.0.0 (released June 2026, `opencv-python` 5.0.0.93) introduces deliberate API breaks and *every* HSV/health-bar recipe, StackOverflow answer, and `rapidocr` compatibility claim on the internet targets 4.x. For a project whose hardest problem is calibration, not compute, adopting a 2-month-old major is uncompensated risk. *(version HIGH — PyPI JSON; 4.x-vs-5.x guidance MEDIUM — opencv.org release notes + search)* |
| **`numpy`** | **2.5.2** | Array backbone for every frame; the bar-fill maths is 3 numpy lines | Non-negotiable — `opencv-python`, `mss` output conversion, `dxcam`, and `windows-capture`'s `to_numpy()` all speak numpy. `opencv-python` declares `numpy>=2` for Python ≥3.9, so the 2.x line is the *supported* line, not the risky one. `numpy` 2.5.2 requires Python `>=3.12` — another reason 3.13 is the floor. *(HIGH — PyPI JSON)* |
| **`requests`** | **2.34.2** | Chatwoot API client | The alert path is: build a string → one `POST` → done. That is `requests`' entire reason to exist. Pair with a `urllib3.util.Retry`-configured `HTTPAdapter` (retry on 429/500/502/503/504, `backoff_factor=1`, `total=3`) so a transient Chatwoot hiccup doesn't silently swallow a death alert. `httpx` 0.28.1 is a fine library but its wins (async, HTTP/2) are irrelevant to a single fire-and-forget POST per event, and its last release was Dec 2024 vs `requests` shipping 2.34.2 currently. *(HIGH — PyPI JSON)* |
| **`rich`** | **15.0.0** | Live console status board | The requirement *"console mostra status em tempo real"* is exactly `rich.live.Live` wrapping a `rich.table.Table`: one row per party member showing name, HP%, MP%, state (ALIVE/DEAD/GONE/BLIND), and last-alert timestamp, repainted at the capture tick. Also gives colour-coded logging via `RichHandler` for free. *(HIGH — PyPI JSON)* |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **`winrt-Windows.Media.Ocr`** + companion namespaces | **3.2.1** | Primary OCR of party-member names | **Always — this is the default OCR engine.** Windows 11 ships an OCR engine (`Windows.Media.Ocr`, available since Win10 1803) that is *free, offline, and already installed*. Since Sept 2023 the Python bindings are modular: you must install **`winrt-Windows.Media.Ocr`, `winrt-Windows.Graphics.Imaging`, `winrt-Windows.Storage`, `winrt-Windows.Storage.Streams`, `winrt-Windows.Globalization`, `winrt-Windows.Foundation`, `winrt-Windows.Foundation.Collections`** — all pip, all wheels, **no system installer**. Requires the language pack to be present (check `C:\Windows\OCR`); `en-US` is present on essentially every Win11 install. *(version HIGH — PyPI/libraries.io; accuracy-on-game-fonts UNVERIFIED — spike it)* |
| **`winrt-ocr-python`** | 0.1.1 (2025‑04‑12) | Convenience wrapper over the above | **Optional.** Wraps the 7-package WinRT dance into `ocr(image) -> text`. Small, single-maintainer, last released April 2025. Use it to prototype fast, but be ready to inline ~40 lines of WinRT calls into our own `ocr_winrt.py` so we don't carry an unmaintained dependency. *(HIGH — PyPI JSON)* |
| **`rapidfuzz`** | **3.14.5** | Fuzzy-match OCR output against the known party roster | **Always.** This is the highest-leverage decision in the OCR section. Party member names are a **closed set of 4–8 strings you already have in config** (`TioMad`, `Kaus`, `Korzis`, `J4guar`). We never need to *read* a name — we need to *classify* a crop into one of N known labels. `rapidfuzz.process.extractOne(ocr_text, roster, scorer=fuzz.WRatio, score_cutoff=70)` turns `"Ti0Mad"` and `"KorzIs"` into correct hits. This collapses the OCR accuracy requirement from "must be right" to "must be roughly right", which is the difference between a working v1 and a rabbit hole. *(HIGH — PyPI JSON)* |
| **`rapidocr`** | **3.9.2** (2026‑07‑21) | Fallback OCR if Windows OCR fails on the L2 font | **Only if the Windows-OCR spike fails.** pip-installable PP-OCR (PaddleOCR models) via ONNX — **no system installer**, which preserves our zero-install property. Costs ~200 MB of deps (`onnxruntime`, `shapely`, `pyclipper`) and a 1–3 s cold start, both irrelevant here because OCR runs *only at init and on composition change* (per PROJECT.md Key Decisions). Declares `opencv_python>=4.5.1.48` and `numpy<3.0,>=1.19.5` — compatible with our pins. *(version + deps HIGH — PyPI JSON)* |
| **`pytesseract`** | 0.3.13 + Tesseract 5.x (UB Mannheim build) | Fallback OCR #2 | **Discouraged for v1.** Best-in-class on *clean, high-contrast, preprocessed* text — which, after 4× upscale + HSV-mask isolation, our name crops arguably are. But it requires a **separate ~100 MB system installer, a `PATH` edit, and a `TESSDATA_PREFIX` environment variable**, and "Tesseract isn't recognized" is famously the #1 support ticket. That directly contradicts the project's non-developer manual-launch constraint. Keep as documented plan C. *(version HIGH — PyPI JSON; install-burden claims MEDIUM — tessdoc + UB Mannheim wiki)* |
| **`dxcam`** | **0.3.0** (2026‑03‑12) | Optional high-FPS capture backend | **Only behind a `capture_backend = "dxcam"` config flag.** Adds real capability: DXGI Desktop Duplication handles **fullscreen-exclusive Direct3D** (where GDI/mss can return black), reaches 240+ FPS, and supports `output_idx` for the second monitor plus native `region=(l,t,r,b)`. Costs: DXGI init can fail on hybrid-GPU laptops, needs a separate camera instance per monitor, and **`grab()` returns `None` when the frame is unchanged since the last grab** — a static/paused game screen at 1 Hz would hand us `None` and a naive loop would misread it as "blind mode". Requires Python `>=3.10`. *(version + API HIGH — PyPI JSON + repo README; `None` semantics HIGH — documented behaviour)* |
| **`windows-capture`** | **2.0.1** (2026‑08‑08) | v2: capture the game window while it is covered by other windows | **Deferred to v2, gated behind a spike.** Rust-backed Windows Graphics Capture bindings. `WindowsCapture(window_name=..., cursor_capture=False, draw_border=False, minimum_update_interval=...)`, callback-driven via `@capture.event def on_frame_arrived(frame, ctrl)`, and `frame.to_numpy()` → `(H, W, 4)` BGRA. Also exposes `DxgiDuplicationSession` as an alternative pipeline. **This is the only candidate that can plausibly read a window buried under a browser** — but see the hard caveat in *Windows 11 Specific Concerns*. *(version + API HIGH — PyPI JSON + windows-capture-python README; occlusion behaviour MEDIUM/UNVERIFIED)* |
| **`pydantic`** | **2.13.4** | Typed config models + startup validation | **Always.** `Config` and `Calibration` as `BaseModel`s means a missing `account_id`, a negative width, or an HSV bound outside 0–179 fails loudly at launch with a field-level message, instead of producing silently-wrong crops at 2am. Costs one dependency; saves the entire class of "why is it reading the wrong pixels" bugs. *(HIGH — PyPI JSON)* |
| **`python-dotenv`** | **1.2.3** (2026‑08‑16) | Load `CHATWOOT_API_TOKEN` from `.env` | **Always.** The Chatwoot access token grants full account API access. It must not sit in the same file the user hand-edits, screenshots for help, or pastes into a Discord. `.env` + `.gitignore` + `.env.example` is the minimum-ceremony correct answer. *(HIGH — PyPI JSON)* |
| **stdlib `tomllib`** | built-in (3.11+) | Read `config.toml` | No dependency. TOML supports **comments**, which matters when a non-developer is editing thresholds. |
| **stdlib `json`** | built-in | Read/write `calibration.json` | The calibration tool must **write** the file. `tomllib` is read-only in stdlib; `json.dump` is not. |
| **stdlib `logging`** | built-in | Rotating event log | `RotatingFileHandler("l2scanner.log", maxBytes=5_000_000, backupCount=3)` — post-farm forensics on false positives is the whole debugging story for this project. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **`uv`** | **0.12.5** — dependency resolution, lockfile, venv, task runner | Single static binary, no bootstrap Python needed. `uv sync` creates and pins `.venv` from `pyproject.toml` + `uv.lock`; `uv run l2-scanner` executes **without any activation step**. This is what makes the `run.bat` a one-liner and eliminates the "did you activate the venv?" support loop. *(HIGH — PyPI JSON)* |
| **`ruff`** | Lint + format | One tool, replaces flake8+isort+black, instant. Zero configuration debate. |
| **HSV trackbar calibrator** (`tools/calibrate_hsv.py`, ~60 lines) | Interactive tuning of `HMin/SMin/VMin/HMax/SMax/VMax` on a live frame | **Build this in Phase 1, not later.** With `Gamma=1.16` on the client, the correct HSV bounds are unknowable a priori — they must be dialled in visually against a real frame. This tool is the single biggest determinant of whether detection works. Writes results straight into `calibration.json`. *(technique MEDIUM — widely-documented standard practice)* |
| **Region-picker tool** (`tools/pick_region.py`) | Drag-select the party window and each member row; persists rects | Uses `cv2.selectROI` on a full-desktop `mss` grab. Beats asking the user to read coordinates off a screenshot. |
| **Frame recorder** (`tools/record.py`) | Dump N raw frames to disk during a real farm session | Lets us replay a genuine death against the detector offline. Without this, every detection bug requires dying in-game to reproduce. |

---

## Installation

```powershell
# 0) Install uv (once, PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 1) Pin the interpreter and create the environment
uv python install 3.13
uv venv --python 3.13
```

`pyproject.toml`:

```toml
[project]
name = "l2-party-scanner"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  # capture
  "mss>=10.2.0",
  # analysis
  "opencv-python>=4.14,<5",
  "numpy>=2.5,<3",
  # OCR (Windows built-in engine — no system installer)
  "winrt-Windows.Media.Ocr>=3.2.1",
  "winrt-Windows.Graphics.Imaging>=3.2.1",
  "winrt-Windows.Storage>=3.2.1",
  "winrt-Windows.Storage.Streams>=3.2.1",
  "winrt-Windows.Globalization>=3.2.1",
  "winrt-Windows.Foundation>=3.2.1",
  "winrt-Windows.Foundation.Collections>=3.2.1",
  # name matching against the known roster
  "rapidfuzz>=3.14.5",
  # chatwoot
  "requests>=2.34.2",
  # config + console
  "pydantic>=2.13.4",
  "python-dotenv>=1.2.3",
  "rich>=15.0.0",
]

[project.optional-dependencies]
# only if the Windows-OCR spike fails on the L2 font
ocr-fallback = ["rapidocr>=3.9.2", "onnxruntime>=1.20"]
# only if mss proves insufficient or user goes fullscreen-exclusive
fastcapture  = ["dxcam>=0.3.0"]
# v2: capture an occluded game window
bgcapture    = ["windows-capture>=2.0.1"]

[project.scripts]
l2-scanner = "l2scanner.__main__:main"

[dependency-groups]
dev = ["ruff>=0.9"]
```

```powershell
uv sync              # resolves + installs + writes uv.lock
uv sync --extra ocr-fallback   # only if needed
uv run l2-scanner    # run it
```

`run.bat` (what the user actually double-clicks):

```bat
@echo off
cd /d "%~dp0"
uv run l2-scanner
pause
```

`calibrate.bat`:

```bat
@echo off
cd /d "%~dp0"
uv run python -m l2scanner.tools.calibrate
pause
```

---

## Windows 11 Specific Concerns

### 1. DPI awareness — the #1 silent-failure bug (**HIGH confidence, must-fix**)

A non-DPI-aware Python process receives **logical** coordinates from Windows while capture APIs return the **physical** pixel buffer. At 125% scaling, a region calibrated at `(1713, 400, 300, 120)` will capture a rectangle offset and sized wrong by 25% — crops land on the wrong pixels and every HSV reading is garbage, with no error message.

**Fix — literally the first executable lines of `__main__.py`, before importing `mss`/`cv2` or creating any window:**

```python
import ctypes
# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except (AttributeError, OSError):
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Win8.1 fallback
```

Microsoft's own docs are explicit: *"You must call `SetProcessDpiAwarenessContext` before you call any APIs that depend on the DPI awareness (including before creating any UI in your process)."* Note the calibration tool and the scanner **must both** call this, or the coordinates the calibrator writes won't mean the same thing to the scanner.

### 2. Multi-monitor with the game on the second display (**HIGH**)

PROJECT.md records `GamePlayViewportStartX=1713`, i.e. the game sits on a secondary monitor.

- `mss.monitors[0]` = the **virtual bounding box of all monitors combined**; `[1]` = primary; `[2]` = second. Capture regions expressed in *virtual desktop* coordinates work directly against `sct.grab({...})` — do **not** try to index into a specific monitor and offset manually.
- **Negative coordinates are legal.** If the user ever drags the game to a monitor positioned left of or above primary, `left`/`top` go negative. Store rects as signed ints and never `abs()` or clamp them.
- `dxcam` does *not* share this model: it needs a **separate camera instance per output** (`dxcam.create(output_idx=1)`), and its `region` is `(left, top, right, bottom)` **relative to that output**, not the virtual desktop. If we ever ship the dxcam backend, the calibration file needs a `coordinate_space` field so the two backends don't silently disagree.

### 3. Windowed vs fullscreen-exclusive (**HIGH**)

The user runs **windowed 1718×1360** — the friendly case. Both `mss` (GDI) and `dxcam` work.

If the user ever switches to **fullscreen exclusive**, GDI-based capture can return black or stale frames while DXGI Desktop Duplication keeps working. Mitigation: detect an all-black / zero-variance frame, log a distinct `CAPTURE_BLACK` state (which the "blind mode" requirement already needs a code path for), and print `Try windowed mode, or set capture_backend = "dxcam"`.

### 4. Occluded and minimized windows — do not over-promise (**MEDIUM, spike required**)

This is the most-misunderstood area and deserves a precise answer:

| Method | Sees a window **covered by another window**? | Sees a **minimized** window? |
|---|---|---|
| `mss` (GDI screen DC) | **No** — it captures the composited desktop *as displayed*. You get the covering window's pixels. | No |
| `dxcam` (DXGI Desktop Duplication) | **No** — same reason; it duplicates the desktop, not a window. | No |
| `windows-capture` (WGC `create_for_window`) | **Probably yes** — DWM maintains a per-window composition surface that WGC reads, so occlusion by *another* window is typically not a blocker. **Unverified for this game.** | **No** — minimized windows stop producing frames; expect black. |
| `pywin32 PrintWindow` + `PW_RENDERFULLCONTENT` | Works for GDI apps; **almost never for DirectX** — returns black for D3D-rendered content. Unreal Engine 2 is D3D. | No |

Two independent reasons WGC may still fail here, both of which the spike must test:
1. **Minimized ≠ occluded.** PROJECT.md already scopes minimized-game as out of bounds ("DirectX para de renderizar"). WGC does not change that.
2. **Unfocused throttling.** Many Direct3D games — and UE2 titles in particular — reduce or halt rendering when they lose focus. If the L2 client stops drawing new frames while alt-tabbed, WGC will faithfully deliver the *last rendered* frame forever, which is worse than a black frame: it looks like valid data and would freeze the HP readings at their pre-alt-tab values, producing **silently stale, non-alerting state**.

**Recommendation:** ship v1 on `mss` with an explicit "keep the game visible" requirement and a robust blind-mode detector. Run a 30-minute spike on `windows-capture` before committing any v2 roadmap phase to it, and make the spike's pass criterion *"HP values continue to change while the game is covered and unfocused"*, not merely *"a non-black frame arrives."*

### 5. `Gamma=1.16` → HSV, and the red-hue wraparound (**MEDIUM-HIGH**)

PROJECT.md already correctly decided HSV over RGB. Two implementation specifics that follow:

- **Red wraps around hue 0 in OpenCV's 0–179 hue scale.** A red HP bar therefore needs **two** `inRange` masks OR'd together — approximately `H∈[0,10]` and `H∈[170,179]` — not one. A single-range red mask is the classic reason a health-bar detector "sometimes reads 0%".
- Blue MP is a single contiguous range, roughly `H∈[100,130]`.
- Gamma primarily lifts **V** (and mildly compresses **S**). Set the **S** lower bound aggressively high (≈120+) so the desaturated grey of the *empty* portion of the bar is rejected, and keep the **V** lower bound generous (≈60) so a gamma-dimmed but still-red pixel isn't discarded. All six bounds go in `calibration.json` — never hardcode them.

### 6. Standard bar-fill measurement technique (**MEDIUM — widely-documented pattern**)

The canonical, contour-free method — three numpy lines, robust, and fast enough to run per-member at 1 Hz:

```python
def bar_fill_ratio(bgr_crop, lo, hi, lo2=None, hi2=None) -> float:
    hsv  = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lo, hi)
    if lo2 is not None:                       # red wraps hue 0 → second range
        mask |= cv2.inRange(hsv, lo2, hi2)

    h = mask.shape[0]
    core = mask[int(h * 0.25): int(h * 0.75)] # drop border/bevel rows
    row  = (core > 0).mean(axis=0) > 0.5      # per-column vote → 1-D profile

    filled = int(np.argmin(row)) if not row.all() else row.size
    return filled / row.size
```

Three deliberate choices worth preserving:
- **Middle-rows-only (`0.25–0.75`)** skips the bar's bevel/border pixels, which are a different colour and skew a naive `countNonZero`.
- **Leading-run (`argmin`) rather than total pixel count.** A bar is filled left-to-right; counting *all* matching pixels lets anti-aliasing speckle or a red icon elsewhere in the crop inflate the reading. Leading-run measures what a human sees.
- **`mean(axis=0) > 0.5` per-column vote** rather than `.any()` makes a single stray red pixel in a column unable to declare that column "filled".

The **presence check** (PROJECT.md's key insight: MP present + HP empty = real death; nothing present = left party or blind) is the same function applied to the MP rect, thresholded as `mp_mask_pixels > min_presence_px`. Store `min_presence_px` in calibration.

### 7. OCR preprocessing for small stylized game fonts (**MEDIUM**)

Both Windows OCR and Tesseract are tuned for document-scale glyphs; L2 name text is ~10–12 px tall. The standard, near-universal fix:

1. Crop the name rect tightly.
2. **Upscale 3–4× with `cv2.INTER_CUBIC`** (or `INTER_LANCZOS4`).
3. Convert to greyscale and, if the name colour is consistent, isolate it with an HSV mask first — that removes the busy game background, which hurts far more than glyph size does.
4. `cv2.threshold(..., cv2.THRESH_BINARY | cv2.THRESH_OTSU)`, then invert if needed so the engine sees **dark text on light background**.
5. Feed to the engine, then **`rapidfuzz` against the roster** — which is what actually delivers correctness.

Per PROJECT.md's own Key Decision, this pipeline runs only at init and on composition change, so its cost is irrelevant.

**Stronger option worth prototyping in the same phase:** skip OCR for known members entirely. On first successful identification, save the name crop to `names/<Member>.png`; thereafter identify rows with `cv2.matchTemplate(crop, saved, cv2.TM_CCOEFF_NORMED)` and a 0.85 threshold. Pixel-identical UI text template-matches at ~1.0 and is *more* reliable than any OCR engine, with no OCR dependency in the hot path. Keep OCR as the bootstrap that populates the template cache.

---

## Chatwoot API — the outbound path (**MEDIUM — API shape verified, delivery model NOT**)

### Endpoint and auth (**HIGH — developers.chatwoot.com**)

```http
POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
api_access_token: <token>
Content-Type: application/json

{ "content": "☠️ TioMad morreu (HP 0%) — 22:41", "message_type": "outgoing" }
```

- Auth is a **flat header**, `api_access_token: <token>` — not `Authorization: Bearer`. This trips people up constantly.
- `message_type`: `"outgoing"` (from agent/bot) or `"incoming"`. We always send `"outgoing"`.
- Optional fields: `private` (bool — a private note is **not** delivered to the contact; must be `false`/omitted), `content_type`, `content_attributes`, and **`template_params`** for WhatsApp templates.
- The token is an **agent/user access token** from Chatwoot Profile Settings. It carries broad account permissions — hence `.env`.

### Getting a `conversation_id` (**MEDIUM**)

There is no "send to phone number" endpoint. The documented sequence is **create contact → create conversation → send message**:

1. `POST /api/v1/accounts/{id}/contacts` → returns `contact` with `id` and a `contact_inboxes[].source_id`
2. `POST /api/v1/accounts/{id}/conversations` with `{"source_id": ..., "inbox_id": ..., "contact_id": ...}` → returns `conversation.id`
3. `POST .../conversations/{conversation_id}/messages`

**For our tool, steps 1–2 should not run at alert time.** Resolve conversation IDs **once** during setup and persist them in `config.toml` as literal integers:

```toml
[chatwoot]
base_url   = "https://chat.example.com"
account_id = 1
# resolve once with `uv run python -m l2scanner.tools.chatwoot_setup`, then paste
conversation_ids = [42]
```

This makes the hot path a single POST with no discovery round-trips, no risk of duplicate contacts, and a trivially testable failure mode.

### Multiple recipients (**MEDIUM**)

Chatwoot has **no broadcast/bulk-send API**. Two viable shapes:

- **(A) One WhatsApp group = one conversation → one POST.** Simplest, cheapest, matches "avisa a galera". **Requires the inbox to be backed by an unofficial WhatsApp provider** (Evolution API / WAHA / Baileys) wired into Chatwoot, because **Meta's official WhatsApp Cloud API does not support sending to groups at all.**
- **(B) N contacts → N conversations → N POSTs** in a loop, each independently retried and logged. More robust to any single failure, N× the API calls, and on the official Cloud API it multiplies the template problem below by N.

Recommend **(A)** if the user's existing setup allows it, **(B)** as the universal fallback. Either way the code should accept a **list** of `conversation_ids` from day one so switching costs nothing.

### 🚩 The single biggest risk in this stack: the WhatsApp 24-hour window (**MEDIUM-HIGH**)

If the user's Chatwoot WhatsApp inbox is backed by **Meta's official WhatsApp Cloud API**, then:

> **Outbound messages to a contact who has not messaged you in the last 24 hours REQUIRE a pre-approved template message** (sent via `template_params`, with the template created and approved in WhatsApp Business Manager).

Our scanner is **purely proactive outbound**. During a long farm session, nobody is replying on WhatsApp. Therefore **most alerts will land outside the 24-hour session window** and a plain `{"content": "..."}` POST will be **accepted by Chatwoot and then silently rejected by Meta** — the worst possible failure mode for an alerting tool. There are open Chatwoot issues confirming friction here (`chatwoot#12699`, `chatwoot#11789`, discussion `#12330`).

**Escape hatches, in order of preference:**
1. **The inbox is a non-official provider** (Evolution API / WAHA). No 24-hour rule, groups supported, free-form text works. Given PROJECT.md says WhatsApp is *"já configurado no servidor do usuário"* and mentions a group, this is plausible — **and if true, the whole risk evaporates.**
2. **Use an approved template** with variables, e.g. `L2 alert: {{1}} {{2}} at {{3}}` → `processed_params: {"1": "TioMad", "2": "morreu", "3": "22:41"}`. Costs one Meta approval cycle and constrains message shape.
3. **Different channel** (Telegram bot, Discord webhook, ntfy) for the always-on alert, keeping WhatsApp for summaries.

**→ This must be a Phase 0 / Phase 1 verification task, executed with a real POST against the user's live Chatwoot before any detection code is written.** Verifying it costs 10 minutes; discovering it after the detector is built invalidates the entire output half of the project. The single most valuable early deliverable is a `--test-alert` flag that sends one message end-to-end and reports whether it actually arrived on a phone.

---

## Config file format

**Decision: two files, both stdlib, split by *who writes them*.**

| File | Format | Written by | Read by | Why |
|------|--------|-----------|---------|-----|
| `config.toml` | TOML | **Human** | `tomllib` (stdlib, 3.11+) | Supports **comments** — essential when a non-developer tunes `death_confirm_frames` or `cooldown_seconds`. No trailing-comma traps. No dependency. |
| `calibration.json` | JSON | **The calibration tool** | `json` (stdlib) | The calibrator must *write* rects and HSV bounds. `json.dump` is stdlib; `tomllib` is **read-only** in stdlib (writing TOML needs `tomli-w`/`tomlkit`). Machine-owned, so comments are irrelevant. |
| `.env` | dotenv | Human, once | `python-dotenv` | `CHATWOOT_API_TOKEN` only. |

The split matters for a concrete reason: **a single file would mean the calibration tool rewrites the user's hand-written settings and comments on every re-calibration.** Machine-written and human-written config must never share a file.

Both files are loaded into `pydantic` models at startup so a malformed value produces `calibration.json → members[2].hp_rect.width: Input should be greater than 0` instead of a wrong crop.

**Why not YAML:** requires `PyYAML`, is whitespace-fragile for a hand-editing non-developer, and carries the "Norway problem" (`no` → `False`) plus the `yaml.load` footgun. Zero upside over TOML here.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `mss` 10.2.0 | `dxcam` 0.3.0 | User switches to **fullscreen exclusive**, or profiling shows capture is the bottleneck (it won't be at 1 Hz). Remember `grab()` → `None` on unchanged frames. |
| `mss` 10.2.0 | `windows-capture` 2.0.1 (WGC) | v2, **after** a successful spike, when "read the game while it's covered by a browser" becomes a real requirement. Does **not** solve minimized. |
| Windows OCR (WinRT) | `rapidocr` 3.9.2 | Windows OCR misreads the L2 font even after 4× upscale + masking. Still pip-only — install burden stays acceptable. |
| Windows OCR (WinRT) | `pytesseract` + Tesseract 5 | Both pip-only engines fail *and* the user accepts a system installer. Strong on clean preprocessed text; weakest on install UX. |
| OCR + `rapidfuzz` | `cv2.matchTemplate` on cached name crops | **Prefer this** once the roster is known — pixel-identical UI text matches at ~1.0. Use OCR only to bootstrap the template cache. |
| `opencv-python` 4.14 | `opencv-python` 5.0.0.93 | After 5.x has a year of field use, or if a 5.x-only feature is needed. Not now. |
| `requests` 2.34.2 | `httpx` 0.28.1 | If the roadmap later adds a concurrent multi-channel fan-out (WhatsApp + Telegram + Discord in parallel). Overkill for v1. |
| `uv` + `run.bat` | `PyInstaller` 6.22.2 one-file EXE | v2, **only if** distributing to party-mates who don't have Python. Budget real time for hidden-import debugging and antivirus false positives. |
| `config.toml` + `calibration.json` | Single `config.json` | Only if you're certain calibration will never be re-run. It will be. |
| One WhatsApp group | N per-contact conversations | Official Meta Cloud API inbox (no group support), or per-person alert routing is desired. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pyautogui.screenshot()` / `PIL.ImageGrab` | Slow (PIL round-trip per frame), **not DPI-aware by default** so `region=` silently captures the wrong rectangle under scaling, and multi-monitor support is sporadic. This is the classic source of "my coordinates are right but the image is wrong". | `mss` + explicit `SetProcessDpiAwarenessContext(-4)` |
| **`pyautogui` at all — do not add it to `requirements`** | It is an *input-synthesis* library. PROJECT.md's hard constraint is *"o scanner é somente leitura, nunca envia input ao jogo"*. Keeping it out of the dependency tree makes that constraint **structurally impossible to violate**, not merely a policy. | Nothing — capture needs no input library |
| `pywin32` `PrintWindow` / `BitBlt` on the game HWND | Returns **black frames for DirectX-rendered content**. `PW_RENDERFULLCONTENT` helps GDI/Chromium windows, not D3D. Unreal Engine 2 is D3D → dead end. Many blog posts recommend this without noting the D3D caveat. | `mss` (visible) or `windows-capture` / WGC (occluded, after spike) |
| `EasyOCR` | Pulls **PyTorch (~2 GB)** into a hobby tool. Roughly 2–3× slower than Tesseract on CPU, and benchmarks consistently show it **weaker than Tesseract/PaddleOCR on small, clean, printed text** — exactly our case. Its strength (curved/rotated/scene text) is irrelevant to a fixed horizontal UI label. | Windows OCR (WinRT), then `rapidocr` |
| `opencv-python` **5.0.0.93** for v1 | Released ~2 months ago with deliberate API breaks. Every HSV/health-bar/`matchTemplate` recipe, and `rapidocr`'s stated compatibility (`opencv_python>=4.5.1.48`), targets 4.x. Zero upside for this workload. | `opencv-python>=4.14,<5` |
| `opencv-python-headless` | Excludes `cv2.imshow`, `cv2.selectROI`, and `cv2.createTrackbar` — **all three are required by the calibration tools**, which are the most important code in this project. | `opencv-python` (full) |
| `PyInstaller` one-file EXE for v1 | Antivirus false positives on one-file PyInstaller bundles are rampant, and a *game-adjacent screen-reading tool* is precisely the profile heuristic scanners quarantine. Add `onnxruntime`/`cv2`/`numpy` hidden-import debugging. The user runs this on their own dev-capable machine and must edit config anyway — so the EXE buys nothing. | `uv run` + `run.bat` |
| Python **3.14** for v1 | Stable since 2025‑10‑07 and a fine language, but wheel coverage for the optional OCR tail (`rapidocr` → `onnxruntime`) is where new-minor gaps historically appear. Zero features here justify the risk. | Python 3.13.x |
| Python **32-bit** | Several WinRT/DXGI-backed wheels are x64-only; you'll hit `no matching distribution` at install time with a confusing message. | 64-bit CPython |
| `PyYAML` / YAML config | Extra dependency, whitespace-fragile for a hand-editing non-developer, `no → False` coercion surprises, `yaml.load` footgun. | `tomllib` + `json`, both stdlib |
| Storing `CHATWOOT_API_TOKEN` in `config.toml` | The token grants broad account API access, and `config.toml` is the file the user will screenshot when asking for help or paste into a chat. | `.env` + `python-dotenv`, `.env` in `.gitignore` |
| Hardcoded HSV constants in source | `Gamma=1.16`, monitor colour profile, and the L2 UI skin make correct bounds machine-specific and *unknowable a priori*. Hardcoding guarantees a rewrite on the first "it doesn't work on my PC". | Every threshold in `calibration.json`, produced by the trackbar tool |
| Contour detection (`findContours`) for bar fill | The common tutorial approach, but it's fragile: it must *find* the bar, so it breaks on partial fill, on 0% HP (no contour at all → indistinguishable from "row missing"), and on adjacent same-colour UI elements. **0% HP is literally the event we must detect.** | Fixed calibrated rect + `inRange` + leading-run column profile |
| Memory reading (`pymem`), packet sniffing, log parsing | Already Out of Scope in PROJECT.md — restated here so the stack can't drift back: memory reads carry real ban risk and break every patch; the protocol is encrypted; the client provably doesn't write chat/events to disk. | Passive screen capture (this stack) |

---

## Stack Patterns by Variant

**If the Chatwoot WhatsApp inbox is an unofficial provider (Evolution API / WAHA / Baileys):**
- Use **one group conversation**, plain `{"content": ..., "message_type": "outgoing"}`.
- No template approval, no 24-hour window, no per-recipient fan-out. The output half of the project is ~40 lines.
- **Verify this first — it is the best case and it collapses the largest risk.**

**If the inbox is Meta's official WhatsApp Cloud API:**
- Groups are **not supported** → fan out over N per-contact `conversation_ids`.
- Create and get approval for **one utility template** with 3 variables (`{{1}}` member, `{{2}}` event, `{{3}}` time) and always send via `template_params` + `processed_params`. Do not branch on "are we inside the 24h window" — always template; it works in both states.
- Budget a Meta approval cycle in the roadmap before the alerting phase can be verified end-to-end.

**If the Windows OCR spike succeeds on the L2 font:**
- Ship OCR-only identification, `rapidfuzz` against the roster, zero system installers. `install` is `uv sync`.

**If the Windows OCR spike fails:**
- Add the `ocr-fallback` extra (`rapidocr`) — still pip-only, install UX preserved.
- **And** build the `matchTemplate` name-crop cache, which sidesteps OCR quality entirely for the steady state.

**If the user later needs the game covered/unfocused (v2):**
- Spike `windows-capture` 2.0.1 with the pass criterion *"HP values keep changing while covered AND unfocused"*.
- Add a **staleness detector** regardless: if every member's HP/MP is bit-identical for > N ticks, enter blind mode. This guards against WGC's silent last-frame-forever failure, and costs ~5 lines.

**If distributing to party-mates (v2):**
- Then, and only then, evaluate `PyInstaller` 6.22.2 `--onedir` (not `--onefile` — better AV behaviour and faster start), and expect to sign the binary or walk people through an AV exclusion.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `numpy` 2.5.2 | Python `>=3.12` | Hard floor. Rules out 3.10/3.11 for the whole project. |
| `opencv-python` 4.14.0.94 | `numpy>=2` (for Python ≥3.9) | The 2.x line is the *supported* line — no `numpy<2` pin needed or wanted. |
| `rapidocr` 3.9.2 | `opencv_python>=4.5.1.48`, `numpy>=1.19.5,<3.0`, Python `>=3.8,<4` | Satisfied by our pins. **Untested against `opencv-python` 5.x** — another reason to stay on 4.x. |
| `dxcam` 0.3.0 | Python `>=3.10` (wheels 3.10–3.14) | Fine on 3.13. Needs a DXGI-capable GPU/driver; can fail on hybrid-graphics laptops. |
| `windows-capture` 2.0.1 | Python `>=3.9`, Windows 10 1803+ | WGC namespace floor is Win10 1803; Win11 is well past it. |
| `winrt-*` bindings 3.2.1 | Windows 10 1803+ | **Modular since Sept 2023** — the old monolithic `winsdk` package is superseded and the top-level namespace reverted from `winsdk` to `winrt`. Install all 7 namespaces or you'll get import errors deep in the call chain. |
| Windows OCR engine | Language pack must be installed | Check `C:\Windows\OCR` for `en-US`. Present on effectively all Win11 installs; validate at startup and fail with a clear message rather than an empty OCR result. |
| `requests` 2.34.2 / `rapidfuzz` 3.14.5 | Python `>=3.10` | Fine on 3.13. |
| `pydantic` 2.13.4 | Python 3.9–3.14 | Fine on 3.13. |
| `PyInstaller` 6.22.2 | Python `>=3.8,<3.16` | Covers 3.13 if v2 needs it. |
| `tomllib` | Python 3.11+ | Stdlib, read-only. Writing TOML would require `tomli-w` — avoided by the two-file design. |

---

## Sources

**Canonical registry / official docs — HIGH (primary source)**
- `https://pypi.org/pypi/{mss,dxcam,windows-capture,opencv-python,numpy,rapidocr,pytesseract,requests,httpx,pydantic,rapidfuzz,rich,python-dotenv,pyinstaller,uv,winrt-ocr-python}/json` — exact current versions, release dates, `requires_python`, declared dependencies
- `https://devguide.python.org/versions/` — Python 3.14 is the current stable (bugfix) release, 3.13 in bugfix until Oct 2029
- `https://developers.chatwoot.com/api-reference/messages/create-new-message` — endpoint path, `api_access_token` header, `message_type` enum, `template_params`
- `https://github.com/NiiightmareXD/windows-capture/tree/main/windows-capture-python` — `WindowsCapture` / `Frame.to_numpy()` / `DxgiDuplicationSession` API
- `https://github.com/ra1nty/DXcam` — `create()`, `grab(region)`, `output_idx`, `output_color`, `None`-on-unchanged-frame semantics
- `learn.microsoft.com` — `SetProcessDpiAwarenessContext`, `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`, `Windows.Graphics.Capture` (Win10 1803+)

**Secondary / community — MEDIUM to LOW (seam tier for `websearch`/`webfetch`: LOW)**
- `opencv.org/opencv-5/` + OpenCV 5 wiki — 4.x and 5.x maintained as parallel stable branches — MEDIUM
- Chatwoot issues `#12699`, `#11789`, discussions `#12330`, `#1572`, `#2198`; `deepwiki.com/chatwoot/chatwoot/7.4-whatsapp-channel` — contact→conversation→message sequence, template requirement outside the 24-hour window — MEDIUM
- `libraries.io/pypi/winrt-Windows.Media.Ocr`, `github.com/hieulhaiwork/winrt-ocr-python` — modular WinRT bindings since Sept 2023, required namespace list, `C:\Windows\OCR` language-pack check — MEDIUM
- OCR accuracy comparisons (`invoicedataextraction.com`, `landeros-labs.com`, `imagetotable.ai`) — Tesseract/PaddleOCR > EasyOCR on small clean printed text; EasyOCR 2–3× slower on CPU — LOW (vendor-adjacent blogs, not benchmarks on game fonts)
- `learncodebygaming.com` (HSV thresholding, fast window capture), `screenshotone.com` (mss vs dxcam throughput), `github.com/szymonszymonszymonv/league-healthbar-detection` — LOW to MEDIUM
- `tesseract-ocr.github.io/tessdoc`, UB Mannheim Tesseract wiki — Windows installer, `PATH` / `TESSDATA_PREFIX` burden — MEDIUM
- OBS forum + `microsoft/WindowsAppSDK#833` — occluded/minimized capture limitations — LOW, **contradictory across sources; this is why the WGC spike is mandatory**

**Known gaps / must be resolved empirically**
1. **Windows OCR accuracy on the L2 XM Essence name font.** No source can answer this. → 20-minute spike with a real screenshot, in Phase 1.
2. **Whether WGC can read the L2 window while occluded *and* unfocused.** Sources conflict; UE2 focus-throttling is the real unknown. → spike before any v2 phase depends on it.
3. **Which WhatsApp provider backs the user's Chatwoot inbox** (official Cloud API vs Evolution/WAHA). **Highest-impact unknown in the entire stack** — determines whether outbound alerts need approved templates and whether group sending is possible. → answer in Phase 0 with a single real `--test-alert` POST.
4. **Whether the L2 client keeps rendering the party window at full fidelity when unfocused but visible.** Affects whether alt-tabbing to a browser while farming is safe. → observable during the same recording session as (1).

---
*Stack research for: real-time screen-scanning game monitor with WhatsApp alerting (Windows 11 / Python)*
*Researched: 2026-08-24*
