---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-08-25T22:11:00.846Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | quick-260825-pik | deviation | l2scanner/loot.py |  | momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu | open |  | 2026-08-25T21:59:50.148Z |  |
| 2 | quick-260825-psq | unmet-truth | l2scanner/ocr.py |  | ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia | fixed |  | 2026-08-25T22:04:27.547Z | 2026-08-25T22:11:00.846Z |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "quick-260825-pik",
    "file": "l2scanner/loot.py",
    "line": null,
    "description": "momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T21:59:50.148Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "quick-260825-psq",
    "file": "l2scanner/ocr.py",
    "line": null,
    "description": "ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-25T22:04:27.547Z",
    "resolved_at": "2026-08-25T22:11:00.846Z"
  }
]
````
