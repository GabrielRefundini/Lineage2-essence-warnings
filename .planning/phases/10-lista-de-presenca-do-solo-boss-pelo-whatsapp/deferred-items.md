# Itens adiados — fase 10

Descobertas fora do escopo do plano em execucao. Registradas para nao se
perderem, e NAO consertadas ali mesmo: a regra do executor e so auto-corrigir
o que a propria tarefa causou.

## Encontrados durante o plano 10-04

### 1. `F401` pre-existente em `tests/test_sessao.py` (linhas 897 e 929)

`VigiaDeManutencao` e importado dentro de dois testes e nunca usado:

```
F401 [*] `l2scanner.manutencao.VigiaDeManutencao` imported but unused
   --> tests/test_sessao.py:897
   --> tests/test_sessao.py:929
```

**Pre-existente, e confirmado como tal:** `python -m ruff check` sobre a versao
do arquivo no commit base (`384bc49`) devolve os MESMOS dois erros. Nenhuma
linha adicionada pelo plano 10-04 os introduziu, e as duas linhas ficam num
bloco (`TestManutencaoNoTick`) que este plano nao encostou.

**Por que nao foi consertado aqui:** os dois imports estao dentro de testes que
usam `_vigia_das_duas_escalas`; remove-los e trivial (`ruff --fix` resolve),
mas mexer num arquivo de teste alheio ao plano durante uma execucao com
commits atomicos mistura a mudanca com o diff que se quer poder ler e reverter
sozinho.

**Como resolver:** `python -m ruff check tests/test_sessao.py --fix` e rodar a
suite. Cabe num `/gsd-quick`.
