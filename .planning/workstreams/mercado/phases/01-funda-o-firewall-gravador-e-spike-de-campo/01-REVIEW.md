---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
reviewed: 2026-08-27T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - l2scanner/gravador.py
  - l2scanner/__main__.py
  - l2scanner/mercado_visao.py
  - l2scanner/calibracao.py
  - tools/conferir_gravacoes_do_spike.py
  - tests/test_gravador_honesto.py
  - tests/test_firewall_escopo.py
  - tests/test_mercado_ancora.py
  - tests/test_calibracao_mercado.py
findings:
  critical: 2
  warning: 8
  info: 5
  total: 15
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-27
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The phase delivers what it claims on the four axes the charter names, and the
four narrow claims hold up under probing:

- `mercado_visao.py` is genuinely standalone — it imports only `numpy` and
  `cv2` and no production module imports `visao.py` or `rastreador.py` from it.
  No coupling to the own-health-bar brightness gate exists.
- The market keys in `calibracao.py` follow the `banner_manutencao` rail
  exactly (`| None = None`, conditional serialization, `.get` on load),
  `VERSAO_DO_ESQUEMA` stays at 2, and the reference fixture loads unmigrated.
- `is_file()` guards are consistent in all three places disk truth is computed
  (`gravador`'s test helper, `tools/conferir_gravacoes_do_spike.pngs_de_frame`,
  and the end-of-session summary in `__main__.py:1730-1732`).
- The firewall's mutation proof is real on both halves: `_banidas_presentes`
  for the predicate, and a fabricated `dist-info` under `tmp_path` for the
  `distributions(path=...)` mechanism that actually covers the `.venv`.
- 53/53 tests in the four new test files pass.

That said, the module that exists to make lying impossible still has two
provable paths where it lies or dies, and the executable gate that decides
whether eight irreplaceable sessions were well spent prints `APROVADO` for a
recording that can contain a single unique frame repeated N times.

Two BLOCKERs and eight WARNINGs follow. Both BLOCKERs are in the recorder
path, which is exactly where the phase promised there would be none.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `Gravador.gravar` breaks its "Nunca levanta" contract on the JSONL write — and kills the whole scanner

**File:** `l2scanner/gravador.py:115-125` (write/flush), contract claim at `l2scanner/gravador.py:86-90`

**Issue:** The `cv2.imwrite` half is wrapped (`_escrever`, lines 127-138), but
the metadata half is not. Lines 121-122 do a raw
`self._arquivo_meta.write(...)` + `.flush()` with no guard. The docstring at
lines 86-90 states flatly:

> "Nunca levanta. `Sessao.tick` chama este metodo ANTES do seu proprio
> try/except, e o laco principal nao envolve o tick em try/except nenhum — uma
> excecao aqui derrubaria o scanner inteiro por causa de disco cheio, levando
> os alertas de morte da party junto."

That is exactly what happens. `sessao.py:199-200` calls `gravar` above the
`try:` at `sessao.py:217`, and `__main__.py:1633` calls `sessao.tick` with no
`try` around it — so the exception unwinds through `laco_principal`, past
`main()`'s two narrow handlers (`JanelaNaoEncontrada`, `ConfiguracaoPerigosa`
at `__main__.py:1969-1979`) and out as a traceback.

Proven on this machine by injecting `OSError(28, 'No space left on device')`
on the metadata handle:

```
LEVANTOU: OSError [Errno 28] No space left on device
frames_gravados 0 falhas 0
```

Three separate defects in one line of output:

1. Disk-full — the single scenario the module names — kills the scanner and
   takes the party death alerts with it. The exact outcome the docstring
   promises cannot happen.
2. `falhas_de_gravacao` stays `0`. The counter that exists to never lie
   reports zero failures for a failed frame.
3. The PNG was already written before the JSONL line was attempted, so the
   folder now holds a `frame_*.png` with no index line. Check 4 of
   `conferir_gravacoes_do_spike.py` (lines == PNGs) will then condemn the whole
   session with "Regrave este cenario" over one metadata hiccup.

`FALHAS_ENTRE_GRITOS` is also unreachable for this class of failure: the
throttle only fires from `_contabilizar_falha`, which this path never reaches.

**Fix:** Route the metadata write through the same failure path, and write the
index *before* claiming the frame — or roll the PNG back when the index fails,
so the disk and the index can never disagree.

```python
if not self._escrever(caminho, imagem):
    self._contabilizar_falha(caminho, "o cv2.imwrite nao confirmou a escrita")
    return False

linha = {
    "indice": frame.indice,
    "momento": momento,
    "saude": frame.saude.value,
    "arquivo": caminho.name,
}
try:
    self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
    self._arquivo_meta.flush()
except Exception:  # noqa: BLE001 - mesmo caminho de falha do imwrite
    # O PNG ja esta no disco e o indice nao vai cita-lo. Um PNG orfao faz a
    # conferencia 4 condenar a sessao inteira, entao ele sai junto.
    caminho.unlink(missing_ok=True)
    self._contabilizar_falha(caminho, "o indice nao aceitou a linha do frame")
    return False

self.frames_gravados += 1
return True
```

Add the matching test to `tests/test_gravador_honesto.py` — the current suite
proves `imwrite` explosions are contained (`test_gravar_nunca_levanta_nem_
quando_o_imwrite_explode`) but never touches the metadata handle, which is why
this survived.

---

### CR-02: In `--record-janela` the PNG and its JSONL line come from two different captures

**File:** `l2scanner/gravador.py:99-121`, driven from `l2scanner/__main__.py:1484` and `l2scanner/__main__.py:1592-1633`

**Issue:** The index line asserts a fact about the file it names that was not
measured on that file.

The tick captures once at `__main__.py:1592` (`frame = fonte.capturar()`).
`frame.pixels`, `frame.saude` and `frame.indice` are all derived from *that*
snapshot of `JanelaSource._ultimo`. The recorder then calls
`self._fonte_completa()` (`gravador.py:101`), which is
`JanelaSource.capturar_completo` (`captura_janela.py:303-311`) — a **second,
independent read** of `_ultimo` under the lock, returning whatever the WGC
callback thread has stored by then.

Between the two reads the tick performs `atender_comandos(...)`
(`__main__.py:1622-1631`), which does a Chatwoot HTTP round-trip. The WGC
callback (`captura_janela.py:257-266`) overwrites `_ultimo` at roughly 38 fps.
So the PNG on disk is routinely tens to hundreds of milliseconds — potentially
a full second, when the network is slow — newer than the pixels that produced
the `saude` recorded beside it.

Consequences, both aimed at this phase's stated purpose:

- The recording is the "base de calibracao e teste de regressao permanente"
  (`gravador.py:3-10`). Replaying `frame_NNNNNN.png` cannot reproduce the
  `saude` the index recorded for it, because that value came from a different
  image. That is a reproducibility hole in the artifact the whole phase exists
  to produce.
- The `momento` field carries the same defect.
- It defeats the fail-closed guard directly above it: `capturar()` can have
  returned `FALHA_DE_CAPTURA` (stale `_ultimo is None`) while
  `capturar_completo()` a moment later returns a real frame, or the reverse.

**Fix:** Capture the window once per tick and derive both the crop and the
recorded PNG from that single array. The cheapest shape that preserves the
current seams is to have `JanelaSource.capturar()` stash the full frame it
actually used and have `fonte_completa` return that same object:

```python
# captura_janela.py, dentro de capturar(), logo apos ler `completo`:
self._completo_do_ultimo_frame = completo   # o MESMO array que gerou o recorte

def completo_do_frame_atual(self) -> np.ndarray | None:
    """A janela QUE PRODUZIU o frame corrente — nao a mais recente.

    `capturar_completo` le `_ultimo` de novo e devolve um frame mais novo:
    o PNG gravado deixaria de ser a imagem de onde saiu a linha do indice.
    """
    return self._completo_do_ultimo_frame
```

and in `__main__.py:1484` bind `fonte_completa = fonte.completo_do_frame_atual`.
A regression test should assert that the recorded PNG is byte-identical to the
window that contained `frame.pixels` even when the source produces new frames
between `capturar()` and `gravar()`.

---

## Warnings

### WR-01: `conferir_gravacoes_do_spike.py` prints APROVADO for a session of frozen frames

**File:** `tools/conferir_gravacoes_do_spike.py:107-215`, verdict at line 270

**Issue:** All five checks are structural (suffix present, index non-empty, no
orphans, count parity, dimensions). None of them looks at `saude`, which the
recorder already writes into every line (`gravador.py:118`).

The failure is reachable, not hypothetical.
`JanelaSource._ultimo` is never cleared, so when the game window stops
producing WGC frames (minimize mid-session, client hang, alt-tab into a
fullscreen app), `capturar_completo()` keeps returning the last good frame
forever. The recorder writes N identical 3.5 MB PNGs, all confirmed, all
correctly dimensioned, all indexed. `_ClassificadorDeSaude`
(`frames.py:131-140`) marks them `CONGELADO` in the JSONL — the evidence is
right there in the file — and the gate ignores it and prints:

> `APROVADO — as 8 gravacoes do spike servem.`

For a 60-second "mercado-aberto" session containing one unique frame. This is
the checkpoint that decides whether the user's eight irreplaceable sessions
were well spent; a green verdict over an unusable recording is the same class
of failure the tool was written to prevent, one level up.

**Fix:** Add a sixth check reading the field that already exists.

```python
SAUDE_INUTIL = {"congelado", "falha_de_captura"}
# Uma sessao majoritariamente congelada tem UM frame util repetido N vezes.
FRACAO_MAXIMA_INUTIL = 0.25

# dentro de conferir_o_indice, no laco que ja faz json.loads(linha):
saudes.append(str(registro.get("saude", "")).lower())
...
ruins = sum(1 for s in saudes if s in SAUDE_INUTIL)
if ruins > len(saudes) * FRACAO_MAXIMA_INUTIL:
    raise Problema(
        f"{pasta.name}: {ruins} de {len(saudes)} frames estao CONGELADO/"
        f"FALHA_DE_CAPTURA. A janela parou de produzir frames e os PNGs sao "
        f"a mesma imagem repetida. Regrave com o jogo visivel e ativo."
    )
```

Consider also asserting that the first and last PNG are not byte-identical —
cheap, and it catches the fully-frozen session outright.

---

### WR-02: The end-of-session summary displays the divergence instead of detecting it

**File:** `l2scanner/__main__.py:1730-1744`

**Issue:** The block computes `no_disco` correctly (with the `is_file()` guard)
and prints it next to `gravador.frames_gravados`, but never compares the two.
The severity is chosen solely by `gravador.falhas_de_gravacao`:

```python
registrar = log.error if gravador.falhas_de_gravacao else log.info
```

So a session where the counter says 118 and the disk says 40 — the exact
scenario named in `tests/test_gravador_honesto.py:9-12` — is emitted at INFO,
in the same style as every routine line, after an hour of farming. The
in-memory counter is precisely the witness that cannot be trusted here (CR-01
shows a path where it stays 0 through a real failure), so deriving the alarm
level from it is fail-open. Printing two numbers side by side is only a check
if something reads both.

**Fix:**

```python
divergiu = no_disco != gravador.frames_gravados
registrar = log.error if (gravador.falhas_de_gravacao or divergiu) else log.info
registrar(
    "Sessao gravada: %d frames confirmados, %d falhas de escrita, "
    "em %s (no disco: %d frame_*.png)%s",
    gravador.frames_gravados,
    gravador.falhas_de_gravacao,
    gravador.pasta,
    no_disco,
    "  <-- DIVERGIU: o contador e o disco discordam, nao confie nesta sessao"
    if divergiu
    else "",
)
```

---

### WR-03: The orphan check accepts any path, and count parity is not set parity

**File:** `tools/conferir_gravacoes_do_spike.py:133-151`

**Issue:** Two gaps in the anti-orphan assertion:

1. `nome = registro.get("arquivo")` is joined with no shape validation:
   `(pasta / nome).is_file()`. On an index that has been hand-edited or written
   by a future tool, `"arquivo": "../mercado-aberto/frame_000001.png"` or an
   absolute path resolves outside the session folder and passes. The check that
   exists to prove "the index does not cite files that do not exist" would
   confirm the existence of a file in another session.
2. Check 4 compares cardinalities (`no_disco != len(linhas)`), not sets. An
   index with a duplicated `arquivo` plus one stray PNG has 10 lines and 10
   files and passes both checks while covering one lost frame.

**Fix:** Constrain the name and compare sets against the same `is_file()`-
filtered listing the count already uses.

```python
import re
NOME_DE_FRAME = re.compile(r"^frame_\d{6}\.png$")

no_disco = {p.name for p in pngs_de_frame(pasta)}
citados: list[str] = []
for numero, linha in enumerate(linhas, start=1):
    ...
    nome = registro.get("arquivo")
    if not isinstance(nome, str) or not NOME_DE_FRAME.match(nome):
        orfaos.append(f"<linha {numero}: 'arquivo' invalido ({nome!r})>")
        continue
    citados.append(nome)

faltando = sorted(set(citados) - no_disco)
sobrando = sorted(no_disco - set(citados))
repetidos = len(citados) - len(set(citados))
# ...cada um com sua Problema propria, nomeando o que aconteceu
```

---

### WR-04: `molde_de_hex` validates only the byte *count*, so transposed dimensions pass

**File:** `l2scanner/mercado_visao.py:151-170`

**Issue:** The docstring promises the guard prevents a silently wrong molde:

> "um `reshape` com dimensao mentida devolveria um molde silenciosamente
> errado, e um molde errado nunca casa com nada: o mercado ficaria invisivel
> sem uma linha de erro."

The implementation only checks `len(brutos) != altura * largura`. Every
factorization of the same product passes. Verified:

```
transposto aceito: (100, 28)
```

A 28x100 anchor whose declared dimensions were swapped decodes to a 100x28
array. `casamento_da_ancora` then hits the `forma.shape[0] > alvo.shape[0]`
guard and returns `0.0` for every frame forever — the market becomes invisible
without a single error line, which is verbatim the outcome the docstring says
is prevented. The same holds for 50x56, 70x40, 14x200, and so on.

The information needed to close this is already in the calibration:
`Calibracao.mercado_ancora` carries the rectangle the molde was cut from
(`calibracao.py:231`), and nothing cross-checks the two.

**Fix:** Take the expected shape as an argument and verify both dimensions.

```python
def molde_de_hex(dados: dict, forma_esperada: tuple[int, int] | None = None) -> np.ndarray:
    altura, largura = int(dados["altura"]), int(dados["largura"])
    if altura <= 0 or largura <= 0:
        raise ValueError(
            f"molde da ancora com dimensao nao-positiva ({altura}x{largura}). "
            f"Recalibre o mercado."
        )
    brutos = bytes.fromhex(dados["bytes"])
    if len(brutos) != altura * largura:
        raise ValueError(...)  # como hoje
    if forma_esperada is not None and (altura, largura) != forma_esperada:
        # O produto bate em toda fatoracao: 28x100 e 100x28 tem 2800 bytes.
        # Um molde transposto nunca casa e o mercado some sem uma linha de erro.
        raise ValueError(
            f"molde da ancora {altura}x{largura} nao bate com o retangulo "
            f"calibrado {forma_esperada[0]}x{forma_esperada[1]}. Recalibre."
        )
    ...
```

and extend `test_dimensao_declarada_mentindo_e_recusada_ALTO` with the
transposed case, which today passes silently.

---

### WR-05: The firewall's declared-requirements sweep is bypassed by PEP 508 direct references and by `-r`/`-e`

**File:** `tests/test_firewall_escopo.py:65`, `tests/test_firewall_escopo.py:113-131`

**Issue:** `_FIM_DO_NOME = re.compile(r"[=<>!~\[\];(,\s]")` does not include
`@`, and line 125 skips every line starting with `-`. Verified against the
real parser:

```
'pyautogui@git+https://github.com/asweigart/pyautogui'
    -> {'pyautogui@git+https://github-com/asweigart/pyautogui'}  banidas: set()
'keyboard@https://example.com/keyboard-0.13.5-py3-none-any.whl'
    -> {'keyboard@https://example-com/...'}                      banidas: set()
'-r extra-requirements.txt' -> set()   banidas: set()
'-e ./vendor/pynput'        -> set()   banidas: set()
```

All four are legal, pip-installable ways to add a banned library to
`requirements.txt` while the declared sweep stays green. The two other sweeps
(running environment, `.venv`) would still catch it *after installation*, but
the declared sweep is the one that is supposed to catch the transitive and the
not-yet-installed — it is described in the module docstring as pegging
"a transitiva DECLARADA antes mesmo de ela ser instalada". A control whose
stated job is pre-installation detection should not be defeated by a syntax
pip accepts.

**Fix:**

```python
# `@` fecha o nome numa referencia direta PEP 508 (`keyboard@https://...`).
# Sem ele o nome vira "keyboard@https://..." e nao casa com a banlist.
_FIM_DO_NOME = re.compile(r"[=<>!~@\[\];(,\s]")
```

and, for the `-` lines, handle the two that carry package names instead of
skipping the whole class:

```python
if linha.startswith(("-r", "--requirement")):
    raise AssertionError(
        f"{linha}: o firewall nao segue includes. Declare tudo no "
        f"requirements.txt, ou ensine a varredura a abrir o arquivo incluido."
    )
if linha.startswith(("-e", "--editable")):
    linha = linha.split(None, 1)[-1]  # o alvo do -e ainda e um pacote
elif linha.startswith("-"):
    continue
```

Add the four strings above to
`test_o_detector_acusa_uma_distribuicao_banida_injetada` as parser-level cases.

---

### WR-06: A folder-name collision silently truncates a previous session's index

**File:** `l2scanner/gravador.py:71-78`

**Issue:** `self.pasta.mkdir(parents=True, exist_ok=True)` followed by
`(self.pasta / "observacoes.jsonl").open("w", ...)`. The folder name has
one-second resolution (`"%Y%m%d-%H%M%S"`), so two recorders that start within
the same second with the same `--rotulo` — two scanner instances, which this
project explicitly supports (`__main__.py:112-114`: "Compartilhada pelas DUAS
instancias que o usuario roda"), or a `run.bat` double-click — land in the same
folder. The second one truncates the first's index to zero while its PNGs stay
on disk, and both then write `frame_000000.png`, `frame_000001.png`, ...
over each other, each believing its own counter.

The result is a corrupted recording that neither process reports. For sessions
described as "o recurso escasso desta fase, porque so ele pode grava-las"
(`gravador.py:104-106`), silent destruction of a prior session is the wrong
default.

**Fix:** Refuse to reuse a folder. The recorder is being created, not resumed.

```python
self.pasta = pasta_base / nome
try:
    # `exist_ok=False`: duas instancias no mesmo segundo com o mesmo rotulo
    # truncariam o indice uma da outra e sobrescreveriam os PNGs, calado.
    self.pasta.mkdir(parents=True, exist_ok=False)
except FileExistsError:
    sufixo = 1
    while True:
        candidata = pasta_base / f"{nome}-{sufixo}"
        try:
            candidata.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            sufixo += 1
            continue
        self.pasta = candidata
        break
```

`"x"` instead of `"w"` on the JSONL open makes the invariant explicit as well.
Note that `pastas_do_sufixo` in the checker globs `*-{sufixo}`, so a
`-1`-suffixed folder would not be picked up — pick a naming scheme that keeps
the label last (e.g. `{carimbo}-{n}-{rotulo}`) or teach the glob about it.

---

### WR-07: The market calibration fields load with zero validation

**File:** `l2scanner/calibracao.py:415-422`

**Issue:** `mercado_molde_da_ancora`, `mercado_limiar_da_ancora` and
`mercado_geometria_da_captura` come straight out of `dados.get(...)` with no
type or range check, into a file the module itself calls user-editable. Three
concrete outcomes:

- `mercado_limiar_da_ancora: 0` or `-1` makes `mercado_aberto` return `True`
  for every crop — a fail-open detector, in the module whose entire charter is
  "a market signal must never become a second death-detector".
- `mercado_limiar_da_ancora: "0.73"` (a quoted number, the single most common
  hand-edit slip) raises `TypeError: '>=' not supported between 'float' and
  'str'` deep inside `mercado_visao.mercado_aberto`, mid-farm, instead of at
  startup with "recalibre".
- `mercado_molde_da_ancora: [1, 2, 3]` raises `TypeError: list indices must be
  integers` inside `molde_de_hex`.

`tests/test_calibracao_mercado.py:115-127` is explicit that the version gate is
"a defesa de entrada (T-02-02)", and `mercado_visao.molde_de_hex:151-159`
states the dict "e ENTRADA NAO CONFIAVEL". The threshold got no equivalent
guard. Nothing consumes these fields yet, which is why this is a WARNING and
not a BLOCKER — but the consumer arrives in Phase 4 and will inherit the hole.

**Fix:** Validate in `carregar`, next to the version gate, where the message
can still say "recalibre" while the user is looking at the console.

```python
limiar = dados.get("mercado_limiar_da_ancora")
if limiar is not None:
    if not isinstance(limiar, (int, float)) or isinstance(limiar, bool):
        raise CalibracaoInvalida(
            f"mercado_limiar_da_ancora precisa ser um numero, veio "
            f"{type(limiar).__name__}. Recalibre o mercado."
        )
    if not 0.0 < limiar <= 1.0:
        # Limiar <= 0 faz TODO recorte virar "mercado aberto" — o detector
        # deixaria de detectar e passaria a afirmar.
        raise CalibracaoInvalida(
            f"mercado_limiar_da_ancora={limiar} fora de (0, 1]. O padrao "
            f"medido e {0.73}. Recalibre o mercado."
        )

molde = dados.get("mercado_molde_da_ancora")
if molde is not None and not isinstance(molde, dict):
    raise CalibracaoInvalida(
        f"mercado_molde_da_ancora precisa ser um objeto com altura/largura/"
        f"bytes, veio {type(molde).__name__}. Recalibre o mercado."
    )
```

Also worth pairing with WR-04: reject a `mercado_ancora` whose
`largura`/`altura` are `<= 0` (`Regiao.de_dict` at `frames.py:93-99` accepts
them), since that rectangle is the cross-check for the molde's shape.

---

### WR-08: A recorder that cannot be constructed takes the whole scanner down

**File:** `l2scanner/__main__.py:1485-1489`, `l2scanner/gravador.py:71-78`

**Issue:** `Gravador.__init__` calls `mkdir` and `open` with no guard, and it
is constructed at `__main__.py:1486` outside any `try`. `main()` only catches
`JanelaNaoEncontrada` and `ConfiguracaoPerigosa` (`__main__.py:1969-1979`), so
a read-only `recordings/`, a full disk, a path locked by an antivirus scanner,
or `recordings` occupied by a file instead of a directory produces a raw
traceback and no scanner at all.

This inverts the doctrine the same file states twice — `montar_despachante`
(`__main__.py:200-205`) and `montar_vigia_de_manutencao`
(`__main__.py:217-222`) both "tenta, degrada com log, devolve None e deixa o
scanner subir. O recurso e opcional; o scanner nao e." Recording is the most
optional feature in the project; it should not be the only one that can refuse
to let the product start.

**Fix:** Give the recorder the same `montar_*` treatment as its two neighbours.

```python
def montar_gravador(args, fonte) -> Gravador | None:
    """Monta o gravador, ou explica por que nao montou. Nunca levanta.

    Mesmo trilho de `montar_despachante` e `montar_vigia_de_manutencao`:
    gravar e opcional, o scanner nao e.
    """
    if not args.record:
        return None
    fonte_completa = fonte.capturar_completo if args.record_janela else None
    try:
        return Gravador(PASTA_GRAVACOES, args.rotulo, fonte_completa=fonte_completa)
    except OSError as erro:
        log.error("GRAVACAO DESATIVADA — nao consegui criar a pasta: %s", erro)
        log.error(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None
```

Note this must log at ERROR, not WARNING: a user running the spike roteiro
needs to abort and fix rather than farm for 60 seconds into nothing.

---

## Info

### IN-01: `mercado_visao.py` has no production consumer, and neither does `mercado_geometria_da_captura`

**File:** `l2scanner/mercado_visao.py` (whole module), `l2scanner/calibracao.py:251`

**Issue:** Nothing under `l2scanner/` imports `mercado_visao`; only
`tests/test_mercado_ancora.py` does. `mercado_geometria_da_captura` is
documented as existing so that "o arranque RECUSAR a leitura de mercado com
'recalibre'", but no startup path reads it. This is correct for a
measurement-only phase and is not a defect today — flagged so it is tracked and
does not quietly become dead code if Phase 4 changes direction.

**Fix:** None now. If Phase 4 slips, add a note in the module docstring naming
the phase that will consume it.

---

### IN-02: "sem calibration.json" is reported when the file exists but is unreadable

**File:** `tools/conferir_gravacoes_do_spike.py:92-104` and `188-194`

**Issue:** `dimensao_do_recorte_da_party` returns `None` for four different
causes — file missing, unreadable, invalid JSON, and no `party_window` key —
and `conferir_a_dimensao` then reports all four as "sem calibration.json nao da
para provar...". A user with a corrupted `calibration.json` is told to run a
calibration they may have already run.

**Fix:** Return a reason alongside the value, or print the swallowed
`OSError`/`JSONDecodeError` to stderr before returning `None`.

---

### IN-03: The structural contract test depends on PEP 563 string annotations

**File:** `tests/test_gravador_honesto.py:81`

**Issue:** `inspect.signature(Gravador.gravar).return_annotation == "bool"`
compares against the *string* `"bool"`, which only holds because
`gravador.py` has `from __future__ import annotations`. Removing that import —
a plausible cleanup once the module drops its `TYPE_CHECKING` block — turns the
annotation into the `bool` type and fails the test for a reason unrelated to
the contract it guards.

**Fix:** `assert inspect.signature(Gravador.gravar).return_annotation in ("bool", bool)`.

---

### IN-04: `--record-janela` is silently ignored by `--so-agenda` and `--testar-manutencao`

**File:** `l2scanner/__main__.py:1883-1898`, `1909-1926`, `1960-1965`

**Issue:** The parse-time validation covers `--replay` and the missing
`--janela`, but `--so-agenda` returns at line 1923 and `--testar-manutencao` at
line 1962, both before `laco_principal` — so `python -m l2scanner --so-agenda
--record-janela --rotulo mercado-aberto` runs happily and records nothing. In
the middle of the eight-session roteiro, that costs a session.

**Fix:** Add to the same validation block:

```python
if args.record and (args.so_agenda or args.testar_manutencao):
    parser.error(
        "--record/--record-janela nao valem com --so-agenda nem com "
        "--testar-manutencao: nenhum dos dois entra no laco que grava."
    )
```

---

### IN-05: The `.venv` sweep skips on a bare directory check

**File:** `tests/test_firewall_escopo.py:186-192`

**Issue:** `test_o_venv_de_producao_nao_tem_biblioteca_de_input` skips whenever
`.venv/Lib/site-packages` is absent. The skip message frames it as "num clone
limpo ou em CI", but it also fires if the venv is relocated or created with a
non-Windows layout — and the sweep that the module docstring calls "a varredura
que fecha o buraco" then reports green-by-skip forever. Low severity here
because `vigiar-party.bat:48-55` hardcodes the same `.venv\Scripts` path and
the directory exists on this machine.

**Fix:** Skip only when no `.venv` exists at all, and fail loudly when a
`.venv` is present but its `site-packages` cannot be located:

```python
if (RAIZ / ".venv").is_dir() and not SITE_PACKAGES_DO_VENV.is_dir():
    candidatos = list((RAIZ / ".venv").glob("**/site-packages"))
    assert candidatos, (
        f"existe um .venv mas nao achei site-packages nele — a varredura que "
        f"cobre o ambiente de producao esta cega, nao verde"
    )
```

---

_Reviewed: 2026-08-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
