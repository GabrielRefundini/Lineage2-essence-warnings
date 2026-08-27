# Itens adiados — fase 10

Descobertas fora do escopo do plano em execucao. Registradas para nao se
perderem, e NAO consertadas ali mesmo: a regra do executor e so auto-corrigir
o que a propria tarefa causou.

## Encontrados durante o plano 10-04

### 1. ~~`F401` pre-existente em `tests/test_sessao.py`~~ — RESOLVIDO pela quick task `260826-vtt` (2026-08-26)

`VigiaDeManutencao` era importado dentro de dois testes e nunca usado:

```
F401 [*] `l2scanner.manutencao.VigiaDeManutencao` imported but unused
   --> tests/test_sessao.py:1037   (em test_as_duas_instancias_competem_pelo_mesmo_marcador)
   --> tests/test_sessao.py:1069   (em test_o_faltam5_tambem_atravessa_a_costura)
```

**Atencao as coordenadas:** este registro nasceu dizendo **linhas 897 e 929**, e
esses numeros envelheceram — o arquivo cresceu para 1168 linhas depois que o
item foi escrito, e no momento do conserto o `ruff` apontava **1037 e 1069**. O
diagnostico estava certo, a coordenada nao. Localize sempre pelo `ruff`, nunca
pelo numero de linha anotado.

**Pre-existente, e confirmado como tal:** `python -m ruff check` sobre a versao
do arquivo no commit base (`384bc49`) devolvia os MESMOS dois erros. Nenhuma
linha adicionada pelo plano 10-04 os introduziu, e as duas linhas ficavam num
bloco (`TestManutencaoNoTick`) que aquele plano nao encostou.

**Por que nao foi consertado ali:** os dois imports estavam dentro de testes que
usam `_vigia_das_duas_escalas`; remove-los e trivial (`ruff --fix` resolve),
mas mexer num arquivo de teste alheio ao plano durante uma execucao com
commits atomicos mistura a mudanca com o diff que se quer poder ler e reverter
sozinho.

**Como foi resolvido:** `python -m ruff check tests/test_sessao.py --fix`, com
escopo no arquivo (nunca no repo: `ruff check .` acusa 31 erros e os outros 29
seguem la de proposito), sem `ruff format`. Diff de duas linhas em um arquivo
so — `1 insercao, 2 delecoes`:

- linha 1037: o `from l2scanner.manutencao import VigiaDeManutencao` foi
  **apagado** — o teste constroi o vigia pelo ajudante, nunca pela classe;
- linha 1069: a linha foi **ENCURTADA, nao apagada**. Ela trazia dois nomes
  (`from l2scanner.manutencao import TipoDeAvisoDeManutencao, VigiaDeManutencao`)
  e `TipoDeAvisoDeManutencao` E usado pelo `assert tipos == [...]` do proprio
  teste — apagar a linha inteira daria `NameError`. E por isso que o conserto
  tinha que ser `ruff --fix`, e nao `sed`.

Sobraram os **2** imports legitimos de `VigiaDeManutencao` (linhas 961 e 989),
que alimentam os `return VigiaDeManutencao(...)` dos ajudantes. Depois do
conserto: `ruff check tests/test_sessao.py` -> `All checks passed!` e a suite
inteira em `1077 passed, 2 skipped`, igual ao baseline.
