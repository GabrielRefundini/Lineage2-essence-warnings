---
phase: quick-260825-cou
plan: 01
subsystem: loot
tags: [whatsapp, comandos, agenda, atomicidade, tdd]
requires: []
provides:
  - "l2scanner/loot.py — RegistroDeLoot, Designacao, nick_para_o_aviso, responder_*"
  - "Comandos .loot-<nick> e .<nick> pelo WhatsApp, com as travas antigas"
  - "Aviso de antecedencia do Solo Boss com 'Loot: X' nos dois lacos"
affects: [comandos, agenda, sessao, __main__]
tech-stack:
  added: []
  patterns:
    - "Marcador atomico O_CREAT|O_EXCL tri-estado (criado/ja_existia/falhou)"
    - "Escrita atomica de JSON via tmp com pid + os.replace"
    - "Comando dinamico com portao por nick conhecido e precedencia do vocabulario fixo"
key-files:
  created:
    - l2scanner/loot.py
    - tests/test_loot.py
  modified:
    - l2scanner/comandos.py
    - l2scanner/agenda.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_comandos.py
    - tests/test_agenda.py
    - tests/test_sessao.py
    - .gitignore
decisions:
  - "Pasta .loot/ propria, sem poda: a poda de 3 dias do .agenda/ apagaria estatistica que e para sempre"
  - "_criar tri-estado: falha de disco MANTEM a designacao (o inverso do marcar da agenda, onde aviso perdido e pior que duplicado)"
  - "Sem eco no grupo nos dois comandos: o grupo fica sabendo pelo aviso de antecedencia com 'Loot: X'"
  - "Consumo so loga, nao manda WhatsApp: 12 bosses/dia, disciplina de volume da agenda"
metrics:
  duration: "14min"
  completed: "2026-08-25"
status: complete
actuals:
  tokens: 16600
  tasks: 3
  commits: 6
---

# Quick 260825-cou: Controle de loot do Solo Boss via comando — Summary

Controle de loot do Solo Boss pelo WhatsApp: `.loot-<nick>` designa quem pega o proximo (e o aviso de antecedencia ganha "Loot: X"), `.<nick>` consulta total e ultimo loot, e o consumo automatico registra em disco exatamente uma vez mesmo com duas instancias — com registro duravel em `.loot/`, que nunca e podado.

## O que foi construido

### Task 1 — `l2scanner/loot.py` (tracer, TDD)
- **RED** `559f3fb`: 41 testes cobrindo registro atomico, corrida de duas instancias, consumo atrasado, JSON corrompido, textos exatos.
- **GREEN** `7f946a0`: dominio puro, stdlib apenas + `l2scanner.agenda`. Gate de imports confirmado (sem `comandos`, `sessao`, `urllib`).
- `RegistroDeLoot` com tres namespaces na mesma pasta: `pegou_{data}-{HHMM}_{slug}` (loot consumado — identidade e o nome do arquivo vazio), `nick_{slug}` (portao do `.<nick>`), `proximo.json` (designacao corrente, escrita via tmp+`os.replace`).
- `_criar` tri-estado: `"criado" | "ja_existia" | "falhou"` — falha de disco mantem a designacao para o proximo tick, em vez de consumir em silencio.
- Tracer verificado end-to-end antes da expansao: suite + gate de imports verdes.

### Task 2 — comandos `.loot-nick` e `.nick` (TDD)
- **RED** `0fafb1e` / **GREEN** `3a0fffc`.
- `interpretar_dinamico(texto, nicks_conhecidos)` olha a primeira palavra CRUA (com hifens — `interpretar` remove hifens do miolo, por isso nao serve aqui). Nick restrito a `[A-Za-z0-9]{2,16}`.
- Portoes provados por teste: `.offline` nunca vira comando; `.palavra` desconhecida morre em silencio; vocabulario fixo tem precedencia (`.status` com "status" nos nicks continua `STATUS`); allowlist de telefone vale para os comandos novos.
- `atender_comandos(..., loot=None)` responde os dois na conversa de origem, sem eco no grupo; sem registro de loot responde "Nao consigo mexer no loot agora."
- `PASTA_LOOT = RAIZ / ".loot"` separada do `.agenda/` (a poda de 3 dias nao alcanca estatistica).

### Task 3 — "Loot: X" no aviso e consumo nos dois lacos (TDD)
- **RED** `4c5b873` / **GREEN** `bfe821d`.
- `texto_do_aviso(aviso, loot=None)`: retrocompativel byte a byte; so o aviso de ANTES ganha ` Loot: {nick}.`; a agenda continua sem conhecer designacao (quem decide e o chamador).
- `Sessao(loot=...)` + `ResultadoDoTick.loot_consumado` estruturado; consumo depois dos avisos para tick deterministico.
- `laco_da_agenda` e `laco_principal` fiados: aviso com nome do designado, consumo so em log (12 ocorrencias/dia — a disciplina de volume da agenda vale aqui tambem).
- Provado por teste: duas `Sessao` na mesma pasta consomem uma unica vez; o boss seguinte sai sem "Loot:"; TvT nunca ganha a linha.

## Verificacao

1. `python -m pytest -q` → **555 passed** (485 na base + 70 novos), sem jogo e sem rede.
2. `python -m pytest tests/test_sessao.py -q -k loot` → 6 passed (fio designar → aviso → consumo → boss seguinte limpo).
3. `git diff --stat` de producao: somente `loot.py` (novo), `comandos.py`, `agenda.py`, `sessao.py`, `__main__.py`. Arquivos de deteccao e transporte (`rastreador`, `visao`, `captura_janela`, `notificador`, `cliente`, `console`, `relogio`) intactos.
4. Em campo (fora do plano): mandar `.loot-j4guar` no privado, conferir a resposta, esperar o aviso com "Loot: J4guar" e, depois do boss, `.j4guar`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] `.loot/` adicionado ao `.gitignore`**
- **Found during:** Task 2
- **Issue:** `.agenda/` ja e ignorado por ser estado local de maquina; `.loot/` tem o mesmo perfil (e ainda mais duravel) e ficaria untracked na primeira execucao real.
- **Fix:** entrada `.loot/` com comentario explicando o porque, ao lado do `.agenda/`.
- **Files modified:** `.gitignore`
- **Commit:** `3a0fffc`

**2. [Rule 1 - Bug no teste] caso de teste com expectativa errada corrigido**
- **Found during:** Task 2 (GREEN)
- **Issue:** o teste RED afirmava que `.loot-j4 guar extra` devolve None, mas a primeira palavra (`.loot-j4`) e uma designacao valida do nick "j4" — palavras extras nao invalidam, mesmo comportamento de `.cancelar silencio`.
- **Fix:** caso trocado por `.loot-j4_guar` (charset realmente invalido).
- **Files modified:** `tests/test_comandos.py`
- **Commit:** `3a0fffc`

## TDD Gate Compliance

Sequencia RED→GREEN cumprida nas tres tasks: `test(cou-01)` → `feat(cou-01)`, `test(cou-02)` → `feat(cou-02)`, `test(cou-03)` → `feat(cou-03)`. Cada RED falhou antes da implementacao (ModuleNotFoundError / ImportError / TypeError verificados). Sem fase REFACTOR — nada a limpar.

## Commits

| Task | Tipo | Hash | Mensagem |
|------|------|------|----------|
| 1 | test | `559f3fb` | o dominio do loot, comecando pela corrida de duas instancias |
| 1 | feat | `7f946a0` | l2scanner/loot.py — o dominio inteiro do loot, puro e testado |
| 2 | test | `0fafb1e` | .loot-nick e .nick — o portao por nick conhecido e as travas antigas |
| 2 | feat | `3a0fffc` | .loot-nick designa e .nick consulta, com as travas antigas valendo |
| 3 | test | `4c5b873` | 'Loot: X' so na antecedencia, e o consumo dentro do tick |
| 3 | feat | `bfe821d` | 'Loot: X' no aviso de antecedencia e o consumo automatico nos dois lacos |

## Self-Check: PASSED

- `l2scanner/loot.py` — FOUND
- `tests/test_loot.py` — FOUND
- Commits `559f3fb`, `7f946a0`, `0fafb1e`, `3a0fffc`, `4c5b873`, `bfe821d` — FOUND no `git log`
- 555 testes passando; gate de imports de `loot.py` verde; arquivos proibidos sem alteracao
