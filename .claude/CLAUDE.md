<!-- GSD:project-start source:PROJECT.md -->

## Project

**L2 Party Scanner**

Um "scanner" que vigia a tela do Lineage 2 XM Essence enquanto o usuário farma em party e avisa no WhatsApp quando algo importante acontece: um membro da PT morreu, saiu do grupo ou ressuscitou. O envio de WhatsApp é feito via API do Chatwoot já configurado no servidor do usuário; a detecção é 100% passiva, por captura e análise de tela (sem tocar no processo do jogo).

**Core Value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.

### Constraints

- **Segurança**: detecção passiva por captura de tela apenas — nunca injetar, ler memória ou enviar input ao jogo (risco de ban zero)
- **Tech stack**: Python no PC do usuário (Windows 11) — mss/dxcam para captura, OpenCV para análise de cor, Tesseract para OCR de nomes, requests para API do Chatwoot
- **Ambiente**: Windows 11, jogo em janela em segundo monitor; script roda na mesma máquina do jogo
- **Latência**: alerta deve chegar em segundos (captura ~1 Hz + debounce ~2-5s + POST no Chatwoot)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

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

## Installation

# 0) Install uv (once, PowerShell)

# 1) Pin the interpreter and create the environment

# only if the Windows-OCR spike fails on the L2 font

# only if mss proves insufficient or user goes fullscreen-exclusive

# v2: capture an occluded game window

## Windows 11 Specific Concerns

### 1. DPI awareness — the #1 silent-failure bug (**HIGH confidence, must-fix**)

# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4

### 2. Multi-monitor with the game on the second display (**HIGH**)

- `mss.monitors[0]` = the **virtual bounding box of all monitors combined**; `[1]` = primary; `[2]` = second. Capture regions expressed in *virtual desktop* coordinates work directly against `sct.grab({...})` — do **not** try to index into a specific monitor and offset manually.
- **Negative coordinates are legal.** If the user ever drags the game to a monitor positioned left of or above primary, `left`/`top` go negative. Store rects as signed ints and never `abs()` or clamp them.
- `dxcam` does *not* share this model: it needs a **separate camera instance per output** (`dxcam.create(output_idx=1)`), and its `region` is `(left, top, right, bottom)` **relative to that output**, not the virtual desktop. If we ever ship the dxcam backend, the calibration file needs a `coordinate_space` field so the two backends don't silently disagree.

### 3. Windowed vs fullscreen-exclusive (**HIGH**)

### 4. Occluded and minimized windows — do not over-promise (**MEDIUM, spike required**)

| Method | Sees a window **covered by another window**? | Sees a **minimized** window? |
|---|---|---|
| `mss` (GDI screen DC) | **No** — it captures the composited desktop *as displayed*. You get the covering window's pixels. | No |
| `dxcam` (DXGI Desktop Duplication) | **No** — same reason; it duplicates the desktop, not a window. | No |
| `windows-capture` (WGC `create_for_window`) | **Probably yes** — DWM maintains a per-window composition surface that WGC reads, so occlusion by *another* window is typically not a blocker. **Unverified for this game.** | **No** — minimized windows stop producing frames; expect black. |
| `pywin32 PrintWindow` + `PW_RENDERFULLCONTENT` | Works for GDI apps; **almost never for DirectX** — returns black for D3D-rendered content. Unreal Engine 2 is D3D. | No |

### 5. `Gamma=1.16` → HSV, and the red-hue wraparound (**MEDIUM-HIGH**)

- **Red wraps around hue 0 in OpenCV's 0–179 hue scale.** A red HP bar therefore needs **two** `inRange` masks OR'd together — approximately `H∈[0,10]` and `H∈[170,179]` — not one. A single-range red mask is the classic reason a health-bar detector "sometimes reads 0%".
- Blue MP is a single contiguous range, roughly `H∈[100,130]`.
- Gamma primarily lifts **V** (and mildly compresses **S**). Set the **S** lower bound aggressively high (≈120+) so the desaturated grey of the *empty* portion of the bar is rejected, and keep the **V** lower bound generous (≈60) so a gamma-dimmed but still-red pixel isn't discarded. All six bounds go in `calibration.json` — never hardcode them.

### 6. Standard bar-fill measurement technique (**MEDIUM — widely-documented pattern**)

- **Middle-rows-only (`0.25–0.75`)** skips the bar's bevel/border pixels, which are a different colour and skew a naive `countNonZero`.
- **Leading-run (`argmin`) rather than total pixel count.** A bar is filled left-to-right; counting *all* matching pixels lets anti-aliasing speckle or a red icon elsewhere in the crop inflate the reading. Leading-run measures what a human sees.
- **`mean(axis=0) > 0.5` per-column vote** rather than `.any()` makes a single stray red pixel in a column unable to declare that column "filled".

### 7. OCR preprocessing for small stylized game fonts (**MEDIUM**)

## Chatwoot API — the outbound path (**MEDIUM — API shape verified, delivery model NOT**)

### Endpoint and auth (**HIGH — developers.chatwoot.com**)

- Auth is a **flat header**, `api_access_token: <token>` — not `Authorization: Bearer`. This trips people up constantly.
- `message_type`: `"outgoing"` (from agent/bot) or `"incoming"`. We always send `"outgoing"`.
- Optional fields: `private` (bool — a private note is **not** delivered to the contact; must be `false`/omitted), `content_type`, `content_attributes`, and **`template_params`** for WhatsApp templates.
- The token is an **agent/user access token** from Chatwoot Profile Settings. It carries broad account permissions — hence `.env`.

### Getting a `conversation_id` (**MEDIUM**)

# resolve once with `uv run python -m l2scanner.tools.chatwoot_setup`, then paste

### Multiple recipients (**MEDIUM**)

- **(A) One WhatsApp group = one conversation → one POST.** Simplest, cheapest, matches "avisa a galera". **Requires the inbox to be backed by an unofficial WhatsApp provider** (Evolution API / WAHA / Baileys) wired into Chatwoot, because **Meta's official WhatsApp Cloud API does not support sending to groups at all.**
- **(B) N contacts → N conversations → N POSTs** in a loop, each independently retried and logged. More robust to any single failure, N× the API calls, and on the official Cloud API it multiplies the template problem below by N.

### 🚩 The single biggest risk in this stack: the WhatsApp 24-hour window (**MEDIUM-HIGH**)

## Config file format

| File | Format | Written by | Read by | Why |
|------|--------|-----------|---------|-----|
| `config.toml` | TOML | **Human** | `tomllib` (stdlib, 3.11+) | Supports **comments** — essential when a non-developer tunes `death_confirm_frames` or `cooldown_seconds`. No trailing-comma traps. No dependency. |
| `calibration.json` | JSON | **The calibration tool** | `json` (stdlib) | The calibrator must *write* rects and HSV bounds. `json.dump` is stdlib; `tomllib` is **read-only** in stdlib (writing TOML needs `tomli-w`/`tomlkit`). Machine-owned, so comments are irrelevant. |
| `.env` | dotenv | Human, once | `python-dotenv` | `CHATWOOT_API_TOKEN` only. |

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

## Stack Patterns by Variant

- Use **one group conversation**, plain `{"content": ..., "message_type": "outgoing"}`.
- No template approval, no 24-hour window, no per-recipient fan-out. The output half of the project is ~40 lines.
- **Verify this first — it is the best case and it collapses the largest risk.**
- Groups are **not supported** → fan out over N per-contact `conversation_ids`.
- Create and get approval for **one utility template** with 3 variables (`{{1}}` member, `{{2}}` event, `{{3}}` time) and always send via `template_params` + `processed_params`. Do not branch on "are we inside the 24h window" — always template; it works in both states.
- Budget a Meta approval cycle in the roadmap before the alerting phase can be verified end-to-end.
- Ship OCR-only identification, `rapidfuzz` against the roster, zero system installers. `install` is `uv sync`.
- Add the `ocr-fallback` extra (`rapidocr`) — still pip-only, install UX preserved.
- **And** build the `matchTemplate` name-crop cache, which sidesteps OCR quality entirely for the steady state.
- Spike `windows-capture` 2.0.1 with the pass criterion *"HP values keep changing while covered AND unfocused"*.
- Add a **staleness detector** regardless: if every member's HP/MP is bit-identical for > N ticks, enter blind mode. This guards against WGC's silent last-frame-forever failure, and costs ~5 lines.
- Then, and only then, evaluate `PyInstaller` 6.22.2 `--onedir` (not `--onefile` — better AV behaviour and faster start), and expect to sign the binary or walk people through an AV exclusion.

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

## Sources

- `https://pypi.org/pypi/{mss,dxcam,windows-capture,opencv-python,numpy,rapidocr,pytesseract,requests,httpx,pydantic,rapidfuzz,rich,python-dotenv,pyinstaller,uv,winrt-ocr-python}/json` — exact current versions, release dates, `requires_python`, declared dependencies
- `https://devguide.python.org/versions/` — Python 3.14 is the current stable (bugfix) release, 3.13 in bugfix until Oct 2029
- `https://developers.chatwoot.com/api-reference/messages/create-new-message` — endpoint path, `api_access_token` header, `message_type` enum, `template_params`
- `https://github.com/NiiightmareXD/windows-capture/tree/main/windows-capture-python` — `WindowsCapture` / `Frame.to_numpy()` / `DxgiDuplicationSession` API
- `https://github.com/ra1nty/DXcam` — `create()`, `grab(region)`, `output_idx`, `output_color`, `None`-on-unchanged-frame semantics
- `learn.microsoft.com` — `SetProcessDpiAwarenessContext`, `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`, `Windows.Graphics.Capture` (Win10 1803+)
- `opencv.org/opencv-5/` + OpenCV 5 wiki — 4.x and 5.x maintained as parallel stable branches — MEDIUM
- Chatwoot issues `#12699`, `#11789`, discussions `#12330`, `#1572`, `#2198`; `deepwiki.com/chatwoot/chatwoot/7.4-whatsapp-channel` — contact→conversation→message sequence, template requirement outside the 24-hour window — MEDIUM
- `libraries.io/pypi/winrt-Windows.Media.Ocr`, `github.com/hieulhaiwork/winrt-ocr-python` — modular WinRT bindings since Sept 2023, required namespace list, `C:\Windows\OCR` language-pack check — MEDIUM
- OCR accuracy comparisons (`invoicedataextraction.com`, `landeros-labs.com`, `imagetotable.ai`) — Tesseract/PaddleOCR > EasyOCR on small clean printed text; EasyOCR 2–3× slower on CPU — LOW (vendor-adjacent blogs, not benchmarks on game fonts)
- `learncodebygaming.com` (HSV thresholding, fast window capture), `screenshotone.com` (mss vs dxcam throughput), `github.com/szymonszymonszymonv/league-healthbar-detection` — LOW to MEDIUM
- `tesseract-ocr.github.io/tessdoc`, UB Mannheim Tesseract wiki — Windows installer, `PATH` / `TESSDATA_PREFIX` burden — MEDIUM
- OBS forum + `microsoft/WindowsAppSDK#833` — occluded/minimized capture limitations — LOW, **contradictory across sources; this is why the WGC spike is mandatory**

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

## Licoes medidas — para os mesmos erros nao voltarem (2026-09-02/03)

Cada regra abaixo tem um numero atras. Nao sao preferencias de estilo; sao o que custou caro.

### 1. Medir SO com codigo de producao

Se voce quer um numero (geometria de celula, semelhanca de molde, recorte, residuo), ESTENDA
a ferramenta existente ou CHAME a funcao de producao (`LeitorDePagina`, `RastreioDoPainel`,
`pontuar_glifos`, `casamento_entre_moldes`, `JanelaSource.capturar_completo`). Nunca
reimplemente por fora "so para conferir".

Por que: tres medicoes de improviso sairam erradas no mesmo dia, todas com a mesma forma —
re-derivar o que a producao ja faz por dentro. Recortar dois moldes em vez de alinha-los deu
`9`x`4` = 0,3162 (o real e 0,0663) e virou uma "refutacao" escrita no fonte que teve de ser
retirada; recalcular a geometria da celula a mao devolveu dez linhas IDENTICAS (as coordenadas
caiam na coluna `Auction List`, cujo texto repete). O mesmo padrao — "um criterio que afirma
que a coisa EXISTE em vez de que foi CHAMADA" — apareceu doze vezes no codigo dos agentes na
mesma sessao. O unico diagnostico que ficou de pe foi o que entrou DENTRO de
`tools/medir_leitura_de_glifo.py`.

Sinal de alarme: resultados identicos onde deveriam variar, ou um numero que confirma a
hipotese rapido demais.

### 2. Criterio de aceite MEDE, nunca afirma existencia

Contar chamadas, comparar a string emitida, injetar entrada conhecida e afirmar a saida.
Nunca `assert "x" in getsource(...)`, nunca `grep` sobre arquivo gitignored, nunca teste que
reimplementa a funcao e mede a copia. Toda mudanca na primeira camada (abaixo) leva prova de
mutacao (quebrar a linha de producao tem de deixar o teste VERMELHO) **e** CONTROLE
(refatorar mantendo a saida tem de ficar VERDE — senao o teste esta preso a forma do codigo
e sera desligado pela primeira pessoa com pressa).

### 3. Processo em camadas — o GSD inteiro so onde ele paga

| a mudanca toca... | processo |
|---|---|
| o leitor, a guarda, a calibracao, um mecanismo novo, qualquer coisa que **decide** sobre dado | GSD inteiro: planner + executor + mutacao + controle |
| texto, formato de log, docs, constante cuja razao ja esta escrita | `/gsd-fast` ou edicao direta com UM teste que mede |

Por que: o planner pagou o proprio custo tres vezes em coisas nao obvias que teriam ido
erradas para producao (tres objetos guardando a fonte de captura; o teto da guarda dobrando
em silencio junto com o limite; os baldes do relatorio serem pelo rotulo PROPOSTO). Mas o
mesmo ritual numa troca de f-string custou ~234 mil tokens por uma edicao de cinco minutos.
Na duvida entre as camadas, e a primeira.

### 4. Pytest: uma rodada por merge, saida inteira

Nunca `| tail -N` (ja escondeu o resumo de 15 falhas), nunca duas rodadas em paralelo, e
nao disparar antes de o merge que ela deveria julgar estar feito. Comando:
`python -m pytest -q --ignore=tests/test_agenda.py` (o aborto ali e um `KeyboardInterrupt`
deliberado). Os skips de OCR sao de ambiente — o pytest roda no python global e as bindings
do Windows moram no `.venv`.

### 5. Tarefa que nao cabe numa janela e tarefa grande demais

Um executor foi cortado por limite de sessao aos 225 mil tokens e teve de ser retomado.
Dividir antes, nao depois.

### 6. Numero que caiu tem de dizer que caiu

Uma frase no fonte que afirma um numero ou um veredito ("o veredito e robusto", "na primeira
ocorrencia ele esta certo", "a ausencia de rate-limit e decisao") e uma promessa. Quando a
medicao a derruba, a frase se reescreve no lugar, com o numero novo e o antigo — nunca se
apaga. Cinco cairam nesta sessao; tres eram do orquestrador.

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

## Worktrees — limpar logo apos mesclar

O isolamento por worktree **fica ligado**: e ele que protege o trabalho em paralelo (foi o que
segurou os "testes fantasmas" quando outro agente commitava no meio de uma rodada). O que NAO
fica e worktree parado depois de mesclado.

**Regra:** quem mescla a branch de um executor remove o worktree e apaga a branch no MESMO
passo — nunca "depois":

    git merge --no-ff worktree-agent-<id> -m "..."
    git worktree remove <caminho> --force
    git branch -D worktree-agent-<id>

**Antes de remover**, conferir que os artefatos soltos (SUMMARY, DRY-RUN, etc.) ja estao
commitados no tronco (`git ls-files --error-unmatch <arquivo>`). Um worktree com alteracao
nao commitada de OUTRO agente nao se apaga: salva-se o diff como patch versionado primeiro
(precedente em `.planning/wip-resgatado/`).

**Por que a regra existe (2026-09-02/03):** acumularam **57 worktrees** — cada um um checkout
completo do repositorio — em dois dias de sessoes. A maquina chegou a 89% de RAM e o app do
Claude morreu duas vezes. O ceifador automatico do GSD (`worktree.reap-orphans`) NAO cobre
isso: ele so recolhe worktrees com arquivo de trava e dono morto, e os criados pela ferramenta
de agentes nao passam por esse protocolo; alem disso exige a branch ja mesclada na branch
PADRAO, e o `master` estava 172 commits atras. Manter o `master` avancado por fast-forward ao
fim de cada bloco ajuda, mas nao substitui a limpeza manual. Conferencia rapida:
`git worktree list` deve mostrar so a pasta principal fora de execucao.

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
