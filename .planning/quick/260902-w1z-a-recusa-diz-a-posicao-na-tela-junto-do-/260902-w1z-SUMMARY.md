---
phase: quick-260902-w1z
plan: 01
quick_id: 260902-w1z
subsystem: mercado
tags: [forense, log, mercado, trava-da-recusa, off-by-one]
status: complete
requires: []
provides:
  - "A recusa do mercado nomeia a POSICAO NA TELA (base 1) junto do indice (base 0)"
  - "A OBSERVACAO do cruzamento nomeia a POSICAO NA TELA junto do indice, no mesmo formato"
affects:
  - l2scanner/mercado_leitura.py
tech-stack:
  added: []
  patterns:
    - "Mutacao obrigatoria + controle de refatoracao para provar que o criterio mede comportamento e nao forma do codigo (pratica entrada no 260902-pqf)"
key-files:
  created: []
  modified:
    - l2scanner/mercado_leitura.py
    - tests/test_mercado_leitura.py
decisions:
  - "Dizer AS DUAS numeracoes (`linha 8 (indice 7)`) em vez de trocar o log para base 1 — o indice continua sendo o numero que viaja no `Descarte`, na chave da trava e nos testes"
  - "A numeracao interna NAO muda: a chave permanece `(int(indice), motivo, detalhe)` em base 0"
  - "As duas citacoes historicas do log de 2026-09-02 18:27 (`mercado_leitura.py:1664` e `:2676`) ficam com a forma ANTIGA — sao transcricoes datadas do que a producao emitiu, e reescreve-las falsificaria o registro"
  - "O mesmo criterio foi reaplicado na segunda tarefa e nao encontrou nenhuma transcricao datada da mensagem de OBSERVACAO — nao havia nada a preservar"
  - "A OBSERVACAO recebeu o mesmo conserto que a RECUSA porque e o mesmo defeito; na aba de NEGOCIACAO ela e a UNICA mensagem que avisa que uma linha nao fecha"
metrics:
  duration: "~28 min"
  completed: 2026-09-02
actuals:
  tokens: 2830
  tasks: 2
  commits: 2
---

# Quick 260902-w1z: A recusa diz a POSICAO NA TELA junto do indice — Summary

`TravaDaRecusa.anunciar` passou a emitir `linha 8 (indice 7) RECUSADA (...)` em vez
de `linha 7 RECUSADA (...)`, corrigindo uma mensagem de forense que apontava
consistentemente uma linha acima da linha real da tela.

## O que mudou

**`l2scanner/mercado_leitura.py`** — a string nasce em um lugar so, e so ele mexeu:

```python
return (
    f"linha {indice + 1} (indice {indice}) "
    f"RECUSADA ({motivo}): {detalhe}"
)
```

A docstring de `anunciar` prometia texto **BYTE-IDENTICO** ao que `log.warning`
renderizava antes da trava existir. Essa promessa morreu nesta tarefa e a
docstring agora registra as quatro coisas exigidas: que o texto mudou em
2026-09-02, por que mudou (a forma estavel apontava para a linha errada, e o
`scanner.log` e a UNICA forense pos-farm do projeto), qual era a forma antiga
(`linha {indice} RECUSADA ({motivo}): {detalhe}`), e que a mudanca foi feita
**PARA** a forense e nao contra ela. Registra tambem que a alternativa de trocar
tudo para base 1 foi RECUSADA, com a razao.

**`tests/test_mercado_leitura.py`**:

- `test_o_INDICE_esta_na_chave_e_e_DELIBERADO` (o assert que ficava em `:2436`)
  foi **atualizado com a razao escrita ao lado**, nao deletado. Ele continua
  sendo o teste que prende a frase byte a byte — a frase e que e outra.
- **Teste novo** `test_a_recusa_diz_a_POSICAO_NA_TELA_junto_do_indice`, que e o
  criterio da tarefa. Ele **mede a string emitida**: `"linha 8 (indice 7)"` para
  o indice 7 e `"linha 1 (indice 0)"` para o indice 0.

## Prova de mutacao (OBRIGATORIA) — VERMELHO confirmado

Trocando `indice + 1` por `indice`, `pytest -q tests/test_mercado_leitura.py -k
"POSICAO_NA_TELA"`, VERBATIM:

```
        setima = TravaDaRecusa().anunciar(7, "cruzamento", "residuo=1000")
        assert isinstance(setima, str)
>       assert "linha 8 (indice 7)" in setima, setima
E       AssertionError: linha 7 (indice 7) RECUSADA (cruzamento): residuo=1000
E       assert 'linha 8 (indice 7)' in 'linha 7 (indice 7) RECUSADA (cruzamento): residuo=1000'

tests\test_mercado_leitura.py:2472: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_mercado_leitura.py::TestATravaDaRecusa::test_a_recusa_diz_a_POSICAO_NA_TELA_junto_do_indice
1 failed, 171 deselected in 0.23s
```

Restaurado, verde de novo: `2 passed, 170 deselected in 0.09s`.

## Controle de refatoracao (OBRIGATORIO) — VERDE, o criterio nao esta preso a forma

A formatacao foi remontada com uma forma de codigo deliberadamente diferente,
mantendo a saida identica:

```python
posicao = "linha " + str(indice + 1) + " (indice " + str(indice) + ")"
causa = "RECUSADA ({0}): {1}".format(motivo, detalhe)
return " ".join([posicao, causa])
```

`pytest -q tests/test_mercado_leitura.py -k "TravaDaRecusa"`, VERBATIM:

```
8 passed, 164 deselected in 1.49s
```

O controle passou: o criterio mede o COMPORTAMENTO (a string emitida) e nao a
FORMA do codigo. Nenhum achado a reportar. A forma final commitada e a do
f-string em duas partes implicitamente concatenadas (a linha unica passaria de
80 colunas).

## Suite

Linha de base medida no arranque desta tarefa, VERBATIM:

```
5371 passed, 85 skipped, 5 warnings in 211.05s (0:03:31)
```

Depois da mudanca, VERBATIM:

```
5372 passed, 85 skipped, 5 warnings in 220.37s (0:03:40)
```

Delta exato de `+1 passed` — o teste novo, e nada mais. Comando em ambas:
`python -m pytest -q --ignore=tests/test_agenda.py`.

## Verificacao dos limites

- `git diff --name-only` saiu exatamente com os dois arquivos do frontmatter:
  `l2scanner/mercado_leitura.py` e `tests/test_mercado_leitura.py`.
- `calibration.json` intacto e NAO commitado (gitignored em `.gitignore:51`;
  nem existe nesta worktree).
- Nada escrito em `.mercado/` — os testes usam so construcao direta de
  `TravaDaRecusa` em memoria. O vigia do mercado nao foi tocado.
- Nenhuma assinatura que carrega indice mudou; `Descarte.indice` e a chave
  `(int(indice), motivo, detalhe)` seguem em base 0.
- `mercado_modo.py:200` (`_recusar` homonimo, recusa de ARRANQUE) nao foi tocado.
- Zero delecoes no commit (`git diff --diff-filter=D HEAD~1 HEAD` vazio).

## Deviations from Plan

None — o plano foi executado exatamente como escrito.

Uma decisao de escopo que o plano nao nomeia mas que vale registrar: as duas
docstrings de `mercado_leitura.py` que citam `linha 5 RECUSADA (cruzamento):
...` (`:1664` e `:2676`) ficaram com a forma ANTIGA de proposito. Elas nao
prometem formato — elas transcrevem, com data e hora, o que a sessao de producao
de 2026-09-02 18:27 emitiu. Reescreve-las trocaria uma citacao verdadeira por
uma falsa.

## Known Stubs

Nenhum.

---

# Segunda tarefa (fora do plano): o irmao gemeo em `TravaDaObservacao`

Pedida pelo coordenador DEPOIS do commit `e9af848`, ao encontrar o mesmo defeito
na mensagem irma. Mesmas regras, segundo commit: **`7908a9a`**.

## O defeito, e por que ele custa MAIS que o da recusa

`TravaDaObservacao.anunciar` (`l2scanner/mercado_leitura.py:1651`) montava
`f"linha {indice} OBSERVACAO do cruzamento: total={total} ..."` com o mesmo
indice base 0, apontando sempre uma linha ACIMA da linha real.

A diferenca que importa esta na aba de **NEGOCIACAO**: la
`mercado_tolerancia_do_cruzamento` e `None` e a guarda so **OBSERVA** — nada e
descartado. Esta e a UNICA mensagem que avisa o usuario de que uma linha nao
fecha, entao apontar para a linha errada e apontar errado justamente onde nao
ha segunda chance. Na recusa o dado ao menos e recusado; aqui a linha entra e
so a mensagem avisa.

## O que mudou

**`l2scanner/mercado_leitura.py`** — o mesmo formato ja decidido pelo usuario:

```python
return (
    f"linha {indice + 1} (indice {indice}) OBSERVACAO do cruzamento: "
    f"total={total} unitario={unitario} quantidade={quantidade} "
    f"residuo={residuo} acima do limite derivado "
    ...
)
```

**A promessa que caiu.** A docstring de `anunciar` dizia:

> O INDICE ENTRA NO TEXTO E NAO NA CHAVE — e onde o usuario olha na grade, e na
> primeira ocorrencia ele esta certo.

Ele **nunca esteve certo** — nem na primeira ocorrencia, porque o erro nao era
de repeticao e sim de base. A docstring foi reescrita registrando que a frase
caiu em 2026-09-02, por que caiu, qual era a forma antiga, e por que o custo
aqui e maior que na irma.

**Nenhum teste lia essa string byte a byte.** Verificado com
`grep -rn "OBSERVACAO do cruzamento" --include=*.py .` e com `grep -rn '"linha '`
sobre `tests/` e `l2scanner/`: a unica leitura era o substring
`assert "OBSERVACAO do cruzamento" in primeiro`
(`test_a_trava_devolve_TEXTO_e_nao_um_booleano`), que atravessa a mudanca
intacto. Nao houve veredito a atualizar — e por isso nenhum teste foi deletado
nem reescrito.

**Teste novo:** `test_a_observacao_diz_a_POSICAO_NA_TELA_junto_do_indice`,
irmao do da recusa, medindo `"linha 8 (indice 7)"` para o indice 7 e
`"linha 1 (indice 0)"` para o indice 0.

## Prova de mutacao (OBRIGATORIA) — VERMELHO confirmado

```
        setima = TravaDaObservacao().anunciar(7, 1880, 600, 3, 80)
        assert isinstance(setima, str)
>       assert "linha 8 (indice 7)" in setima, setima
E       AssertionError: linha 7 (indice 7) OBSERVACAO do cruzamento: total=1880 unitario=600 quantidade=3 residuo=80 acima do limite derivado 3.0. A guarda esta DESLIGADA (medicao do 02-02 REPROVADA) — nada foi descartado.
E       assert 'linha 8 (indice 7)' in 'linha 7 (indice 7) OBSERVACAO do cruzamento: total=1880 unitario=600 quantidade=3 residuo=80 acima do limite derivado 3.0. A guarda esta DESLIGADA (medicao do 02-02 REPROVADA) — nada foi descartado.'

tests\test_mercado_leitura.py:2233: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_mercado_leitura.py::TestATravaDaObservacaoDoCruzamento::test_a_observacao_diz_a_POSICAO_NA_TELA_junto_do_indice
1 failed, 172 deselected in 0.30s
```

Restaurado, verde: `1 passed, 172 deselected in 0.10s`.

## Controle de refatoracao (OBRIGATORIO) — VERDE

Formatacao remontada com forma de codigo deliberadamente diferente:

```python
posicao = "linha " + str(indice + 1) + " (indice " + str(indice) + ")"
numeros = "total={0} unitario={1} quantidade={2} residuo={3}".format(...)
limite = "{0:.1f}".format(limite_derivado_do_cruzamento(quantidade))
return " ".join([posicao, "OBSERVACAO do cruzamento:", numeros, ...])
```

`pytest -q tests/test_mercado_leitura.py -k "Observacao or POSICAO_NA_TELA"`,
VERBATIM:

```
10 passed, 163 deselected in 0.80s
```

**E o controle foi conferido de verdade, e nao so pelos asserts.** Como o teste
novo mede substrings, um controle que mudasse a saida em algum ponto FORA do
prefixo passaria despercebido. A saida das duas formas foi capturada e comparada
por igualdade de string completa (198 caracteres):

```
BYTE-IDENTICO: True
'linha 8 (indice 7) OBSERVACAO do cruzamento: total=1880 unitario=600 quantidade=3 residuo=80 acima do limite derivado 3.0. A guarda esta DESLIGADA (medicao do 02-02 REPROVADA) — nada foi descartado.'
```

Forma de codigo diferente, saida identica, teste verde: o criterio mede
COMPORTAMENTO. Nenhum achado a reportar. A forma commitada e a do f-string.

## Suite (linha de base remedida no arranque desta segunda tarefa)

```
5372 passed, 85 skipped, 5 warnings in 122.78s (0:02:02)
```

Depois:

```
5373 passed, 85 skipped, 5 warnings in 140.96s (0:02:20)
```

Delta exato de `+1 passed`. Comando em ambas:
`python -m pytest -q --ignore=tests/test_agenda.py`.

## Verificacao dos limites (segunda tarefa)

- A lista de arquivos modificados saiu com os mesmos dois do frontmatter e
  nenhum outro.
- Chave da trava intacta: `(int(total), unitario, int(quantidade))`, sem indice.
  `Descarte` intacto. Nenhuma assinatura que carregue indice mudou.
- Nada escrito em `.mercado/`; o vigia nao foi tocado. `calibration.json` segue
  ausente desta worktree e nao commitado. `recordings/` nao foi lido.
- Zero delecoes no commit `7908a9a`.

## Criterio de escopo reaplicado (o coordenador pediu, e mantive)

`grep -rn "OBSERVACAO" --include=*.py l2scanner/` devolveu seis ocorrencias, e
**nenhuma e transcricao datada** da mensagem: sao comentarios sobre o conceito
("o residuo e OBSERVACAO e existe para o..."), nao citacoes de log de producao.
Diferente da recusa, aqui nao havia nada a preservar — o criterio foi aplicado
e simplesmente nao teve sobre o que incidir.

## Descoberta lateral que reforca o formato escolhido

O `+ 1` em texto de usuario ja era convencao da casa antes desta tarefa, em duas
areas independentes:

- `l2scanner/batismo.py:378` — `f"  {apelido} (vi na linha {pendente.indice + 1})"`
- `l2scanner/calibrar.py:1586` — `f"a linha {indice + 1} estava vazia?"`

As duas travas do mercado eram as excecoes, e agora nao sao mais.

## Self-Check: PASSED

Tarefa 1 (recusa):

- `l2scanner/mercado_leitura.py` — FOUND (`TravaDaRecusa.anunciar`)
- `tests/test_mercado_leitura.py` — FOUND (`test_a_recusa_diz_a_POSICAO_NA_TELA_junto_do_indice`)
- commit `e9af848` — FOUND no historico

Tarefa 2 (observacao):

- `l2scanner/mercado_leitura.py` — FOUND (`TravaDaObservacao.anunciar`)
- `tests/test_mercado_leitura.py` — FOUND (`test_a_observacao_diz_a_POSICAO_NA_TELA_junto_do_indice`)
- commit `7908a9a` — FOUND no historico

---

## Verificacao independente do orquestrador

Mutacao refeita em worktree isolado sobre o merge, derrubando os DOIS `+ 1` de uma vez:

| | |
|---|---|
| linha de base | `17 passed, 156 deselected in 2.00s` |
| os dois `indice + 1` viram `indice` | `3 failed, 14 passed` |

Os tres que caem sao `test_a_observacao_diz_a_POSICAO_NA_TELA_junto_do_indice`,
`test_a_recusa_diz_a_POSICAO_NA_TELA_junto_do_indice` e
`test_o_INDICE_esta_na_chave_e_e_DELIBERADO` — este ultimo cai porque a chave da trava e a
mensagem deixam de concordar sobre qual numero e qual, que e exatamente a confusao que a tarefa
existe para acabar.

Varredura de fecho: `grep -n 'f"linha {indice}' l2scanner/mercado_leitura.py` sai VAZIO. Nao
sobrou mensagem do mercado com indice cru.

## A ORIGEM, e ela e do orquestrador

O plano desta tarefa cobriu SO a recusa. A observacao — irma gemea, mesmo arquivo, mesmo log —
ficou de fora porque eu li o defeito pelo sintoma que o usuario relatou em vez de varrer o
arquivo atras da forma. A varredura que a acharia (`grep -rn 'linha {indice'`) custa uma linha e
eu so a rodei DEPOIS do merge da primeira metade.

E a observacao era a PIOR das duas: ela e a mensagem que sai na aba de NEGOCIACAO, onde
`mercado_tolerancia_do_cruzamento` e `None` e a guarda apenas OBSERVA — ali ela e o UNICO aviso
de que uma linha nao fecha, e apontar para a linha errada e apontar errado onde nao ha segunda
chance. Consertar so a recusa teria deixado o pior dos dois de pe, com a sensacao de resolvido.

## O achado do executor que vale guardar

A docstring de `TravaDaObservacao` nao trazia so uma promessa de FORMATO — ela afirmava que o
numero estava CERTO: *"e onde o usuario olha na grade, e na primeira ocorrencia ele esta certo"*.
Nunca esteve, nem na primeira: o erro era de BASE, e nao de repeticao. Uma frase que afirma
correcao e mais perigosa que uma que so descreve forma, porque ela desencoraja a conferencia.
