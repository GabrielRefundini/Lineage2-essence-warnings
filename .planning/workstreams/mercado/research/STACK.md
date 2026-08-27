# Stack Research — Mercado (captura passiva de preços do World Exchange)

**Domain:** Leitura de dígitos de fonte fixa de UI de jogo + série temporal local de preços
**Researched:** 2026-08-27
**Confidence:** HIGH — os fatos decisivos foram verificados **na máquina-alvo**, não em docs

## TL;DR — The Prescriptive Answer

| Concern | Decision | One-line why |
|---|---|---|
| (a) Leitura de dígitos | **`cv2.matchTemplate` template-por-dígito** (10 glifos + separador) — a mesma técnica do `identidade.py` | Fonte de UI determinística = mesmos pixels toda vez; o projeto já **mediu** 1.000 vs 0.454 de margem com máscara + recorte justo |
| (a) Segmentação de glifos | **Projeção de colunas via numpy** sobre a máscara de texto | Já temos a máscara claro-e-dessaturado; achar vãos entre glifos é `mask.any(axis=0)` + runs — zero deps |
| (b) Armazenamento | **`sqlite3` stdlib** (SQLite **3.49.1** no venv real, verificado), tabela STRICT, WAL, `busy_timeout` | Duas instâncias escrevem na mesma pasta; SQLite resolve concorrência que CSV/JSONL não resolve |
| (b) Mediana/percentis | **`SELECT` da janela → `statistics.median`/`statistics.quantiles`** (stdlib) | `median()`/`percentile_cont()` **não existem** no build do CPython — verificado empiricamente |
| (b) Tendência | **`statistics.linear_regression`** (stdlib, 3.10+) ou `numpy.polyfit` já presente | Slope de preço×tempo em uma linha, zero deps |
| (c) Gráfico no console | **Sparkline em blocos Unicode (`▁▂▃▄▅▆▇█`) sobre o console ANSI existente** | O console do projeto é stdlib puro (não é rich); uma sparkline são ~15 linhas |
| **Novas dependências** | **ZERO** | Tudo que a feature precisa já está na árvore ou na stdlib |

## Recommended Stack

### Core Technologies (nada novo — só o que muda de papel)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **`cv2.matchTemplate` (opencv-python, já instalado)** | `>=4.10,<5` (pin atual do `requirements.txt`; 4.14.0.94 é a corrente) | Classificar cada glifo de dígito contra 10-12 templates; classificar o nome do item contra a watchlist | É literalmente a técnica já validada em produção no `identidade.py` para nomes: conjunto fechado + renderização determinística → **classificação, não leitura**. Medição do próprio projeto: máscara de texto + recorte justo dá correlação 1.000 no acerto e 0.454 no erro. Dígitos são um conjunto ainda mais fechado (10 glifos) e a fonte de preço da UI é fixa. *(HIGH — evidência empírica do próprio repo + prática consolidada: PyImageSearch credit-card OCR, reconhecimento de displays 7-segmentos)* |
| **`sqlite3` (stdlib)** | SQLite **3.49.1** — **verificado no venv da máquina do usuário** (Python 3.12.10) | Série temporal `(item, preço, quantidade, timestamp)` em arquivo local | Zero dependência, transacional, e — crucial — o usuário roda **duas instâncias** (Yazalaque/Faerlina) na mesma pasta. WAL + `busy_timeout` dá escrita concorrente segura que append em CSV/JSONL não dá. Verificado no build real: window functions OK, `ENABLE_MATH_FUNCTIONS` OK, JSON OK, tabelas STRICT OK, WAL OK. *(HIGH — testado localmente)* |
| **`statistics` (stdlib)** | built-in | `median`, `quantiles(n=100)` (percentis), `linear_regression` (tendência), `fmean` | O build do sqlite3 do CPython **não tem** `median()`/`percentile_cont()` (verificado: `OperationalError: no such function`). A extensão percentile só entrou no amalgamation no SQLite 3.51.0 (2025-11-04) e vem **desligada** por padrão (`-DSQLITE_ENABLE_PERCENTILE`). Solução correta nesta escala: `SELECT preco FROM ... WHERE item_id=? AND ts>=?` e computar em Python — dezenas de milhares de linhas são microssegundos. *(HIGH — testado localmente + sqlite.org/percentile.html)* |
| **`numpy` (já instalado)** | `>=2.0` (pin atual) | Projeção de colunas para segmentar glifos; máscara de texto; `polyfit` se quiser tendência ponderada | Já é a espinha dorsal de todo frame. A segmentação de dígitos é `mask.any(axis=0)` + detecção de runs — 10 linhas. *(HIGH)* |
| **`datetime`/`zoneinfo` (stdlib)** | built-in | Timestamps UTC (epoch int) no banco; exibição em hora local no console | Mesma disciplina do `loot.py`: tempo entra por parâmetro, armazenado como inteiro epoch UTC — ordena, indexa e compara sem parsing. *(HIGH)* |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **WinRT OCR (`l2scanner/ocr.py`, já na árvore)** | `winrt-*>=3.2.1` (já instalado para o banner de manutenção) | **Só bootstrap opcional** de templates de nome de item da watchlist | Se recortar manualmente os nomes dos itens na calibração for chato, o OCR existente pode sugerir o rótulo do recorte **uma vez**, na ferramenta de calibração. Nunca no caminho quente. Para dígitos, nem isso: são 10 glifos, recorta-se à mão em minutos. |
| **`json` (stdlib)** | built-in | Metadados dos templates de dígito (`calibration.json` já existe) | Geometria das colunas da janela do Exchange (nome, preço, quantidade), retângulos de linha e limiares da máscara vão no `calibration.json`, escritos pela ferramenta de calibração — padrão já estabelecido. |
| **`tomllib` (stdlib)** | built-in | Watchlist de itens no `config.toml` | Itens vigiados são decisão humana com comentários — mesma razão do split config/calibration já decidido no v1. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Ferramenta de captura de templates de dígito** (`tools/` ou `l2scanner/calibrar.py` estendido) | Recortar os 10 dígitos + separador de milhar a partir de um frame real do Exchange | Construir **na primeira fase** da workstream, como o calibrador HSV foi no v1. Um preço conhecido na tela (ex.: "1.234.567" ou "1,234,567") contém quase todos os glifos de uma vez. Persistir como PNGs em `l2scanner/recursos/` (padrão já existente: `dialogo_desconexao.png`). |
| **Gravador de frames existente (`gravador.py`)** | Gravar sessões reais da janela do Exchange para replay offline | Já existe para a party window; apontar para a região do mercado. Todo bug de leitura de preço vira reprodutível sem abrir o jogo. |
| **`sqlite3` CLI / `python -m sqlite3`** | Inspecionar o banco durante desenvolvimento | Nada a instalar; `python -c "import sqlite3..."` já resolve. |

## Design Notes (o que o planner precisa saber)

### (a) Dígitos — template-por-dígito, e por que nada além disso

1. **Pipeline:** recorte da célula de preço (retângulo calibrado) → máscara claro-e-dessaturado (receita do `identidade.py`) → projeção de colunas (`mask.any(axis=0)`) → runs contíguos = glifos → cada glifo classificado por `matchTemplate` (`TM_CCOEFF_NORMED`) contra os 10-12 templates → maior score ganha; score máximo abaixo de limiar (~0.8) = leitura inválida, **descarta o frame inteiro** (nunca grava um preço meio-lido).
2. **Separador de milhar é um template também** (e o separador decimal, se houver). Na montagem do número, separadores são simplesmente ignorados: `int("".join(digitos))`. Não usar `locale` — a UI do jogo não muda com o locale do Windows.
3. **Validação cruzada barata:** re-ler o mesmo preço em 2 frames consecutivos antes de gravar. Fonte determinística → leituras devem ser idênticas; divergência = frame de transição (scroll, hover) → descarta. Custa zero e elimina a classe inteira de erro de captura em movimento.
4. **Por que não OCR:** exatamente o argumento já vencedor do `identidade.py` — um glifo errado inventa um preço plausível e ninguém desconfia. Dígito trocado em preço é o pior modo de falha possível para análise de mercado (um "1.234.567" lido como "7.234.567" contamina min/max/mediana). Classificação com limiar de confiança falha **fechado** (descarta); OCR falha **aberto** (inventa).

### (b) Série temporal — schema e consultas

```sql
PRAGMA journal_mode=WAL;          -- duas instâncias, escrita concorrente
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;        -- suficiente com WAL; perda máxima = último checkpoint

CREATE TABLE IF NOT EXISTS itens (
    id     INTEGER PRIMARY KEY,
    nome   TEXT NOT NULL UNIQUE    -- o rótulo da watchlist do config.toml
) STRICT;

CREATE TABLE IF NOT EXISTS observacoes (
    id         INTEGER PRIMARY KEY,
    item_id    INTEGER NOT NULL REFERENCES itens(id),
    preco      INTEGER NOT NULL CHECK (preco > 0),      -- adena inteira; NUNCA float
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    ts         INTEGER NOT NULL                          -- epoch UTC, segundos
) STRICT;

CREATE INDEX IF NOT EXISTS idx_obs_item_ts ON observacoes(item_id, ts);
```

- **Preço como INTEGER.** Adena não tem centavos; float acumula erro e quebra igualdade em dedup.
- **Dedup na inserção, não na consulta:** antes de inserir, comparar com a última observação do mesmo item; se `(preco, quantidade)` idênticos e `ts` recente (janela configurável, ex.: 60 s), pular. Sem isso, 1 Hz com a janela aberta grava 3.600 linhas idênticas por hora e a "mediana" vira a mediana do tempo-de-janela-aberta, não do mercado.
- **Consultas de análise:** `min`/`max`/`avg`/`count` direto em SQL (uma passada no índice). Mediana e percentis: `SELECT preco FROM observacoes WHERE item_id=? AND ts>=? ORDER BY ts` → `statistics.median(precos)`, `statistics.quantiles(precos, n=100)`. Tendência: `statistics.linear_regression(ts_list, precos)` → sinal do slope. Nesta escala (milhares a centenas de milhares de linhas por item), o round-trip Python é invisível.
- **Um arquivo `mercado.db` na pasta do projeto**, ao lado de `logs/` — não misturar com `.agenda/`/`.loot/` (que são marcadores de arquivo com semântica própria de poda/consumo).

### (c) O que mais? Nada que exija dependência

- **Console:** o console do projeto é ANSI stdlib puro (verificado em `l2scanner/console.py` — não é rich, ao contrário do que o CLAUDE.md sugere). Uma sparkline de blocos Unicode (`▁▂▃▄▅▆▇█`) para a tendência de cada item são ~15 linhas sobre o que já existe.
- **Watchlist:** lista de nomes de item em `config.toml`; templates dos nomes em `recursos/` gerados pela calibração — espelho exato do fluxo de nomes da party.

## Installation

```bash
# NADA a instalar. requirements.txt não muda.
# sqlite3, statistics, json, tomllib, datetime, zoneinfo: stdlib.
# cv2, numpy: já na árvore.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Template-por-dígito (matchTemplate) | WinRT OCR (já instalado) para os dígitos | Nunca para o caminho quente. Só se a fonte de preço se provar **não-determinística** (anti-aliasing variável por posição) E a margem de matchTemplate cair abaixo de ~0.15 entre acerto e segundo colocado — medir na spike, como foi medido para nomes. |
| Projeção de colunas para segmentar | `matchTemplate` deslizante da célula inteira + picos ordenados por x | Se os glifos encostarem (kerning negativo) e a projeção não achar vãos. Mesmo custo, mesma lib; é um fallback de implementação, não de stack. |
| `sqlite3` stdlib | Append em JSONL (padrão do `outbox.jsonl` existente) | Só se a análise fosse "última leitura" sem consultas históricas. Aqui a pergunta é "mediana dos últimos 7 dias por item" com dois processos escrevendo — é o caso de uso do SQLite, não de append de linha. |
| Mediana em Python (`statistics`) | `conn.create_aggregate("median", ...)` em Python registrado no SQLite | Se um dia a consulta precisar de mediana **por grupo** numa query só (ex.: mediana de 50 itens de uma vez). Funciona hoje, mas é mais código para o mesmo resultado; row-by-row callback é mais lento que o fetch+statistics. |
| `statistics.linear_regression` | `numpy.polyfit(ts, precos, 1)` | Indiferente — numpy já está na árvore. `polyfit` se quiser pesos (observações recentes valendo mais). |
| Epoch int UTC no banco | ISO-8601 TEXT | Nunca aqui: int compara/indexa mais rápido e elimina parsing. ISO só se o banco fosse lido por humanos direto — não é; o console traduz. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`pandas`** | ~60 MB de dependência para `median()` e `min()/max()` em listas de milhares de números. Viola o stdlib-first sem comprar nada nesta escala. **Limiar de justificativa:** análise multi-item com resample/rolling/join que passe de ~200 linhas de numpy+statistics artesanal. | `statistics` + numpy já presente |
| **`duckdb` / `polars`** | Motores analíticos para dados que cabem numa lista Python. Mesma categoria de exagero. | `sqlite3` + `statistics` |
| **`sqlean.py` / `pysqlite3` (para ganhar `median()` no SQL)** | Troca o sqlite3 da stdlib por um binário de terceiro só para evitar 3 linhas de Python. A extensão percentile do SQLite (≥3.51.0) vem desligada por padrão de qualquer forma. **Limiar:** só se medição mostrar o fetch+Python lento — não vai mostrar nesta escala. | `SELECT` + `statistics.median` |
| **`sqlite-utils` / `peewee` / SQLAlchemy** | ORM/helper para UMA tabela com UM índice. O SQL cru cabe em ~40 linhas de módulo. | `sqlite3` cru, padrão `loot.py` de disciplina |
| **OCR (qualquer engine) para dígitos de preço** | Falha aberto: um glifo errado grava um preço plausível e envenena a série para sempre. Template com limiar falha fechado (descarta o frame). O projeto já rejeitou OCR para conjunto fechado uma vez — dígitos são o conjunto mais fechado que existe. | Template-por-dígito + limiar + dupla leitura |
| **`pytesseract`/Tesseract** | Já descartado no v1 (instalador de sistema, PATH, TESSDATA). Nada mudou. | — |
| **CSV com `csv` stdlib como banco** | Sem índice, sem transação, e duas instâncias fazendo append concorrente corrompem linha. Consulta de "últimos 7 dias" vira scan do arquivo inteiro. | `sqlite3` WAL |
| **Preço como REAL/float** | Igualdade quebrada (dedup falha), erro acumulado em agregação. Adena é inteira. | `INTEGER` + `CHECK (preco > 0)` |
| **`matplotlib`/`plotext`/`asciichartpy` para gráfico** | O requisito é "análise mostrada no console" — o console ANSI existente + sparkline de blocos resolve. **Limiar:** o usuário pedir explicitamente gráfico histórico navegável — aí `plotext` (puro Python, ~sem deps) é o candidato, não matplotlib. | Sparkline Unicode sobre `console.py` |

## Stack Patterns by Variant

**Se a fonte do Exchange se provar determinística (esperado — mesma engine que renderiza os nomes):**
- Template-por-dígito com limiar 0.8+, dupla leitura em frames consecutivos.
- Porque: é o caso já medido no `identidade.py` — correlação 1.000 no acerto.

**Se a spike mostrar glifos com renderização variável (anti-aliasing dependente de posição/fundo):**
- Primeiro tentar upscale 2-4× do recorte + máscara antes do match (barato).
- Só então considerar o fallback WinRT OCR **com validação**: aceitar apenas leituras que casem `^\d{1,3}([.,]\d{3})*$` e que se repitam em 2 frames.

**Se a série crescer além de ~10 milhões de linhas (anos de captura densa):**
- Adicionar uma tabela de agregados diários (`item_id, dia, min, max, mediana, n`) preenchida em manutenção no arranque, e consultar percentis longos sobre ela.
- Porque: mantém o fetch+Python instantâneo sem trocar de motor. Ainda zero deps.

**Se as duas instâncias precisarem vigiar itens diferentes:**
- Mesmo `mercado.db` para as duas — WAL aguenta; o dedup por item torna a escrita concorrente inofensiva. Não criar um banco por instância (a análise quer a série unificada).

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| **Python real do venv: 3.12.10** | tudo recomendado | **Atenção:** o CLAUDE.md diz "Python 3.13.x", mas o venv verificado é 3.12.10. Nenhum item desta pesquisa exige 3.13 — `statistics.linear_regression` é 3.10+, `tomllib` 3.11+, STRICT tables são do SQLite (3.37+), não do Python. **Não há razão para upgrade de interpretador neste milestone.** |
| SQLite **3.49.1** (bundled, verificado) | window functions (3.25+), math functions (compilado com `ENABLE_MATH_FUNCTIONS`, verificado), STRICT (3.37+), WAL | `median()`/`percentile_cont()` **ausentes** — extensão percentile só entra no amalgamation em 3.51.0 e desligada por padrão; não contar com ela nem após upgrade de Python. |
| `opencv-python>=4.10,<5` (pin atual) | numpy>=2.0 (pin atual) | Nada muda; `matchTemplate` e as ferramentas de calibração (`selectROI`, trackbars) já são o motivo do pacote completo. |
| `sqlite3` stdlib | duas instâncias concorrentes | WAL exige que o banco fique em disco local (está) — WAL não funciona em rede/SMB. `busy_timeout` obrigatório nos dois processos. |

## Sources

- **Verificação empírica na máquina-alvo (2026-08-27)** — `.venv` real: Python 3.12.10, SQLite 3.49.1; testado ao vivo: window functions OK, math functions OK (`ENABLE_MATH_FUNCTIONS` nas compile options), JSON OK, STRICT OK, WAL OK, `median()`/`percentile_cont()` → `no such function` — **HIGH (evidência direta)**
- `l2scanner/identidade.py` (repo) — medições reais de matchTemplate com máscara + recorte justo: 1.000 acerto / 0.454 erro — **HIGH (evidência direta)**
- `l2scanner/console.py`, `l2scanner/notificador.py`, `requirements.txt` (repo) — console é ANSI stdlib, entrega é urllib, árvore real de deps é mínima — **HIGH (evidência direta)**
- [The Percentile Extension — sqlite.org](https://sqlite.org/percentile.html) — extensão no amalgamation desde 3.51.0 (2025-11-04), desligada por padrão (`-DSQLITE_ENABLE_PERCENTILE`); `median(X)` ≡ `percentile_cont(X,0.5)` — **MEDIUM (websearch, cruzado com teste local)**
- [Built-in Aggregate Functions — sqlite.org](https://sqlite.org/lang_aggfunc.html) — agregados do core (sem mediana) — **MEDIUM**
- [Credit card OCR with OpenCV and Python — PyImageSearch](https://pyimagesearch.com/2017/07/17/credit-card-ocr-with-opencv-and-python/) e [Digit Recognition for 7-Segment Displays — Medium](https://mansoormemon.medium.com/digit-recognition-for-7-segment-displays-using-template-matching-a-simple-approach-6a52951beddf) — template-por-dígito como técnica padrão para fontes fixas — **MEDIUM (websearch, cruzado com a evidência do próprio repo)**
- [OpenCV: Template Matching (docs 4.x)](https://docs.opencv.org/4.13.0/d4/dc6/tutorial_py_template_matching.html) — semântica de `TM_CCOEFF_NORMED` — **MEDIUM**
- [cpython issue #86852](https://github.com/python/cpython/issues/86852) — math functions habilitadas nos builds do CPython — **MEDIUM (confirmado localmente)**

---
*Stack research for: captura e análise de preços do World Exchange (workstream mercado)*
*Researched: 2026-08-27*
