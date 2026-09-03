---
phase: quick-260902-syn
plan: 01
subsystem: ferramentas-de-medicao
tags: [medicao, glifo, diagnostico, refutacao, mercado]
status: complete

requires:
  - l2scanner.mercado_leitura._alinhar_por_preenchimento
  - l2scanner.mercado_visao.casamento_da_ancora
  - l2scanner.mercado_visao.glifos_de_calibracao
  - Calibracao.mercado_limiar_de_leitura_de_glifo
  - Calibracao.mercado_margem_de_leitura_de_glifo
provides:
  - tools/medir_leitura_de_glifo.py::fragilidade_por_rotulo
  - tools/medir_leitura_de_glifo.py::imprimir_a_fragilidade_por_rotulo
  - tools/medir_leitura_de_glifo.py::casamento_entre_moldes
  - tools/medir_leitura_de_glifo.py::construir_analisador
  - "chave de linha de comando --por-rotulo"
affects:
  - tools/medir_leitura_de_glifo.py
  - tests/test_medir_leitura_de_glifo.py

tech-stack:
  added: []
  patterns:
    - "funcao PURA sobre a populacao ja varrida, impressor separado"
    - "composicao de simbolos de PRODUCAO importados, nunca reescritos"
    - "mutacao + mutacao de CONTROLE como par obrigatorio de prova"

key-files:
  created: []
  modified:
    - tools/medir_leitura_de_glifo.py
    - tests/test_medir_leitura_de_glifo.py

decisions:
  - "A chave de fragilidade e a TAXA DE RECUSA (uniao das duas travas de producao, normalizada por n). O pior score isolado e a mediana foram REJEITADOS e a rejeicao esta escrita no fonte."
  - "Trava ausente sai None e AUSENTE, nunca zero: zero e uma medicao, ausente e a falta de uma. E uma taxa computada com metade das travas subestimaria em silencio."
  - "As travas vem da CALIBRACAO (as que estao valendo), nunca o par PROPOSTO pelo RELATORIO 1, que e hipotese."
  - "`_alinhar_por_preenchimento` (privado de producao) e IMPORTADO em vez de a ferramenta padronizar o proprio alinhamento: preencher da 0,1918 onde cortar da 0,5000, entao uma copia mediria outra coisa com o mesmo nome."
  - "O `9` sai INOCENTADO como problema de score; a busca se move para `segmentar_glifos` e a geometria da coluna."

metrics:
  duration: ~50min
  completed: 2026-09-02

actuals:
  tokens: 31000
  tasks: 2
  commits: 2
---

# Quick 260902-syn: A medicao de glifo passa a relatar score por rotulo — Summary

A ferramenta que ja varria as 8 gravacoes do censo passou a QUEBRAR POR ROTULO a
distribuicao que ela so agregava, ordenada pela taxa de recusa das duas travas de
producao — e o `9` acusado por palpite em campo saiu INOCENTADO por numero, com a
proxima medicao nomeada.

## O que foi construido

**Task 1 — `fragilidade_por_rotulo`** (commit `7b096f4`)

Funcao PURA sobre a lista de `Amostra` que `varrer` ja produz: nao varre, nao le
arquivo, nao imprime, nao mexe na lista recebida. Devolve uma linha por rotulo com
`n`, os quatro quantis de score, os quatro de margem, as duas contagens abaixo das
travas e a `taxa_de_recusa`. Ordem por taxa decrescente, desempate deterministico
por `score_p1`, `margem_p1`, `rotulo`.

O impressor `imprimir_a_fragilidade_por_rotulo` REUSA `_quantis` — o formato
`n/min/p1/p5/mediana/max` continua com uma casa so. A chave `--por-rotulo` e
aditiva e nasce falsa; `construir_analisador()` foi extraida de `main` sem mudar
nenhum texto de ajuda, nome de chave ou padrao.

**Task 2 — `casamento_entre_moldes` e as tres refutacoes** (commit `5b0eb8b`)

Duas linhas compondo os DOIS simbolos de producao — a mesma composicao de
`pontuar_glifos:670-680`. As tres refutacoes entraram na docstring do modulo, na
voz das duas que ja estavam la.

## O veredito sobre o `9`: INOCENTADO como problema de score

Execucao real, `--por-rotulo` e **sem `--gravar`**, 8 gravacoes, 55.342 glifos,
travas configuradas piso `0,4698` / margem `0,0370`:

```
==============================================================================
RELATORIO POR ROTULO - QUEM ESTA EM APUROS, ORDENADO POR RECUSA
==============================================================================
  as travas CONFIGURADAS: piso 0.4698  margem 0.0370
  (sao as da calibracao, as que estao VALENDO - nunca o par PROPOSTO pelo RELATORIO 1, que e hipotese)
  os baldes sao pelo rotulo PROPOSTO, nunca pela verdade: um `9` lido como `4` cai no balde do `4`.

  '6'  n=2440   abaixo do piso 1241    abaixo da margem 655     recusa 53.4%
      score  n=  2440  min=-0.0146  p1=0.0264  p5=0.0800  mediana=0.4679  max=1.0000
      margem n=  2440  min=0.0011  p1=0.0050  p5=0.0117  mediana=0.1598  max=0.4029
  '4'  n=5170   abaixo do piso 2332    abaixo da margem 1640    recusa 45.1%
      score  n=  5170  min=-0.1292  p1=-0.0892  p5=-0.0605  mediana=0.4698  max=1.0000
      margem n=  5170  min=0.0005  p1=0.0017  p5=0.0022  mediana=0.3004  max=0.9337
  '7'  n=2334   abaixo do piso 908     abaixo da margem 137     recusa 38.9%
      score  n=  2334  min=-0.0270  p1=0.0000  p5=0.0756  mediana=1.0000  max=1.0000
      margem n=  2334  min=0.0001  p1=0.0025  p5=0.0302  mediana=0.4992  max=0.4992
  '3'  n=2221   abaixo do piso 780     abaixo da margem 599     recusa 35.2%
      score  n=  2221  min=-0.0192  p1=0.0326  p5=0.0607  mediana=1.0000  max=1.0000
      margem n=  2221  min=0.0000  p1=0.0000  p5=0.0000  mediana=0.3451  max=0.3451
  '8'  n=4097   abaixo do piso 1379    abaixo da margem 1126    recusa 33.7%
      score  n=  4097  min=-0.0454  p1=0.0497  p5=0.1441  mediana=0.7242  max=1.0000
      margem n=  4097  min=0.0000  p1=0.0000  p5=0.0000  mediana=0.1266  max=0.3117
  '5'  n=4568   abaixo do piso 1484    abaixo da margem 200     recusa 32.5%
      score  n=  4568  min=-0.0157  p1=0.0654  p5=0.1858  mediana=0.9439  max=1.0000
      margem n=  4568  min=0.0000  p1=0.0067  p5=0.0380  mediana=0.2945  max=0.3451
  ','  n=11446  abaixo do piso 3639    abaixo da margem 2097    recusa 31.8%
      score  n= 11446  min=-0.1235  p1=-0.0789  p5=-0.0572  mediana=1.0000  max=1.0000
      margem n= 11446  min=0.0002  p1=0.0062  p5=0.0157  mediana=0.8082  max=0.8082
  '1'  n=3670   abaixo do piso 764     abaixo da margem 237     recusa 21.0%
      score  n=  3670  min=-0.0634  p1=0.0251  p5=0.1243  mediana=1.0000  max=1.0000
      margem n=  3670  min=0.0007  p1=0.0088  p5=0.0280  mediana=0.8428  max=0.8428
  '9'  n=2904   abaixo do piso 515     abaixo da margem 332     recusa 17.8%
      score  n=  2904  min=-0.0152  p1=0.0710  p5=0.2118  mediana=0.8367  max=1.0000
      margem n=  2904  min=0.0000  p1=0.0020  p5=0.0132  mediana=0.3397  max=0.5219
  '0'  n=14224  abaixo do piso 2491    abaixo da margem 283     recusa 17.5%
      score  n= 14224  min=-0.0493  p1=0.0430  p5=0.2988  mediana=0.9258  max=1.0000
      margem n= 14224  min=0.0001  p1=0.0127  p5=0.0406  mediana=0.1579  max=0.2890
  '2'  n=2268   abaixo do piso 152     abaixo da margem 114     recusa 6.9%
      score  n=  2268  min=-0.0279  p1=0.0090  p5=0.2532  mediana=1.0000  max=1.0000
      margem n=  2268  min=0.0000  p1=0.0000  p5=0.0363  mediana=0.4992  max=0.4992

  OS DOIS PARES, REMEDIDOS AGORA (molde contra molde):
    '9' x '4' = 0.0663   (a semelhanca ACUSADA em campo, e refutada)
    '0' x '8' = 0.7110   (o par mais estreito do sistema)
```

**INOCENTA POR AUSENCIA.** O balde do `'9'` — recusa **17,8%**, `score_p1`
**0,0710**, `margem_p1` **0,0020** — e o TERCEIRO MAIS SAUDAVEL dos onze rotulos;
so `'2'` (6,9%) e `'0'` (17,5%) recusam menos. O `9` que a ferramenta ve, ela le
com folga. O erro de campo nao veio do score do `9` estar fraco.

**ACUSA POR CAUDA.** O balde do `'4'` — recusa **45,1%**, `score_p1` **-0,0892**,
`margem_p1` **0,0017** — e o SEGUNDO PIOR dos onze, atras so do `'6'` (53,4%), e um
dos DOIS unicos com `score_p1` negativo (o outro e a virgula). Como os baldes sao
pelo rotulo **PROPOSTO**, um `9` lido como `4` cai ali e nunca aparece no balde do
`9`. As duas linhas apontam para o mesmo lado.

**A PROXIMA MEDICAO, NOMEADA.** Isto NAO prova que a cauda do `4` seja feita de
`9`. Prova que a cauda existe, que e grande (2.332 abaixo do piso em 5.170) e que
e ali que um glifo estrangeiro estaria sentado. Cada `Amostra` guarda
`(gravacao, arquivo, linha, coluna)`, entao a cauda do `4` abaixo do piso e
reconferivel frame a frame; a pergunta a responder e **quantos daqueles recortes
sao `9` na tela**. Ate la, a busca se move para `segmentar_glifos` e para a
geometria da coluna — os dois lugares onde um `9` deixa de virar um run de `9`.

## As quatro provas

Todas as quatro rodaram; as linhas de resumo estao verbatim nos commits.

| # | Prova | Esperado | Resultado |
|---|-------|----------|-----------|
| 1 | MUTACAO Task 1 — ordem por taxa invertida | VERMELHO nos Testes 1, 3, 4, 5 | `4 failed, 8 passed, 5321 deselected in 1.27s` |
| 2 | CONTROLE Task 1 — uniao por conjunto de indices, linha por atribuicao | VERDE | `12 passed, 5321 deselected in 1.07s` |
| 3 | MUTACAO Task 2 — molde comparado contra si mesmo | VERMELHO nos 1 e 2, VERDE no 3 | `2 failed, 1 passed, 5333 deselected in 4.88s` |
| 4 | CONTROLE Task 2 — locais nomeados colapsados, ordem dos argumentos PRESERVADA | VERDE | `3 passed, 5333 deselected in 4.30s` |

As duas mutacoes quebraram exatamente os testes previstos, e as duas de controle
seguraram. Na Task 2 o Teste 3 (ancora de sanidade) ficou VERDE sob a mutacao,
como o plano previu — e a demonstracao de que ele sozinho nunca bastaria.

## Deviations from Plan

### [Rule 3 — Blocking] A base da suite veio abaixo da referencia do plano, e NAO por teste perdido

- **Found during:** medicao da base, antes da primeira linha de codigo
- **Referencia do plano (em `77531ce`):** 5260 passed, 61 skipped
- **Medido nesta worktree:** **5236 passed, 85 skipped**
- **Investigacao:** o unico commit entre `77531ce` e o HEAD desta task e `ac23caf`,
  que e o commit de DOCS do proprio plano — a arvore de codigo e identica. O total
  COLETADO e o mesmo nos dois: 5260+61 = 5236+85 = **5321**. Nenhum teste foi
  perdido; 24 passaram de `passed` para `skipped`.
- **Causa:** os 24 skips a mais sao condicionais de AMBIENTE, nao de codigo — as
  mensagens dizem `recordings/ e gitignored e nao existe neste checkout` (esta
  worktree nao tem `recordings/`) e `Este Python nao tem as bindings de OCR do
  Windows` (o python global nao tem as WinRT).
- **Decisao:** o gatilho de parada do plano existe para pegar "alguem perdeu teste
  no caminho", e o total coletado identico prova que ninguem perdeu. Segui, e
  adotei **5236 passed / 85 skipped** como a base desta worktree.
- **Ao fim:** **5251 passed, 85 skipped** — exatamente 5236 + 15 testes novos (12 da
  Task 1, 3 da Task 2), skips inalterados, zero regressao.

### [Achado] A remedicao DISCORDA de um dos dois numeros da REFUTACAO 1

Nao e desvio de execucao — e o achado que a remedicao existe para produzir, e esta
registrado no fonte.

O plano manda escrever que `9`x`4` = **0,3162** acromatico contra `0`x`8` =
**0,7110**. A ferramenta, na composicao de PRODUCAO, mede:

| Par | Registrado no plano | Medido pela ferramenta |
|-----|--------------------|------------------------|
| `0` x `8` | 0,7110 | **0,7110** — identico na quarta casa |
| `9` x `4` | 0,3162 | **0,0663** |

A mesma mecanica reproduz um numero exatamente e nao reproduz o outro. Isso
desloca a suspeita para o **0,3162**, que provavelmente saiu de outra variante
(outro alinhamento, ou o par cromatico) e nao da composicao que a producao usa.
**Nao ha explicacao medida para a diferenca, entao nenhuma foi escrita no fonte** —
so o fato, os dois numeros e a data.

A CONCLUSAO nao se mexe em nenhuma das duas leituras: por 0,3162 ou por 0,0663, o
`9` e o `4` estao muito abaixo do par mais estreito do sistema, e a refutacao fica
de pe com folga MAIOR do que a registrada. Os dois numeros ficam na docstring do
modulo, com a discordancia nomeada.

## As tres refutacoes gravadas no fonte

Na docstring de `tools/medir_leitura_de_glifo.py`, secao propria:

1. **Os moldes `9` e `4` NAO se parecem** — 0,3162 registrado / 0,0663 remedido,
   contra `0`x`8` = 0,7110, o par mais estreito. Remedido a cada `--por-rotulo`, e
   `TestOsMoldesQueNaoSeParecem` prende a ordem em clone limpo (0,0663 contra
   0,6952 sobre os moldes das fixturas).
2. **A coluna do incremento NAO e cortada pela borda** — termina em x=1179 numa
   janela de 1720 px, 541 px de folga, com o metodo escrito junto do numero.
3. **O arnes JOGADO FORA** — script avulso que recalculou a geometria da celula A
   MAO e devolveu as dez linhas de uma pagina identicas, porque as coordenadas
   caiam na coluna `Auction List`, cujo texto se repete em toda linha. E a razao
   escrita de este trabalho ter entrado na ferramenta que JA usa geometria de
   producao, em vez de num script novo.

## Restricoes honradas

- **NENHUM molde tocado.** `mercado_templates_de_digito` segue com 13 moldes.
- **`mercado_limiar_de_leitura_de_glifo` (0,4698) e `mercado_margem_de_leitura_de_glifo`
  (0,0370) inalterados** — verificado no `calibration.json` do checkout principal
  depois da execucao. O relatorio os LE e nunca os propoe.
- **`mercado_tolerancia_do_cruzamento` segue `None`.**
- **A ferramenta NUNCA rodou com `--gravar`.** Confirmado por fonte: `gravar()` tem
  um unico ponto de chamada, sob `if opcoes.gravar:`.
- **Nada sob `l2scanner/` mudou.** `git diff --name-only ac23caf HEAD` lista
  exatamente os dois caminhos do plano.
- **`calibration.json` nunca commitado**, **`.mercado/` nunca escrito**,
  **`recordings/` so lido pela varredura NOMEADA de 8 gravacoes** (nenhum glob novo).
- **Nenhuma dependencia nova**, nenhuma biblioteca de sintese de input.
- **Zero delecoes** nos dois commits; sem `--amend`, sem `stash`; `VERSAO_DO_ESQUEMA`
  intacta.

## Known Stubs

Nenhum. As duas funcoes tem implementacao completa, e todo caminho de trava ausente
imprime AUSENTE em vez de um valor substituto.

## Self-Check: PASSED

- `tools/medir_leitura_de_glifo.py` — FOUND, com `fragilidade_por_rotulo`,
  `imprimir_a_fragilidade_por_rotulo`, `casamento_entre_moldes`,
  `construir_analisador`
- `tests/test_medir_leitura_de_glifo.py` — FOUND, com `TestAFragilidadePorRotulo`
  (12 testes) e `TestOsMoldesQueNaoSeParecem` (3 testes)
- commit `7b096f4` — FOUND
- commit `5b0eb8b` — FOUND
- `git diff --name-only ac23caf HEAD` — exatamente os dois caminhos, sem delecao
- suite completa: 5251 passed, 85 skipped (base 5236 + 15 novos)

---

## Verificacao independente do orquestrador

**A discrepancia da REFUTACAO 1 esta explicada, e a culpa e do orquestrador.** O executor
registrou honestamente que remediu `9`x`4` = 0,0663 contra os 0,3162 que eu tinha afirmado, sem
inventar explicacao por nao ter medicao para ela. A explicacao existe e foi medida agora:

    o metodo do ORQUESTRADOR (recorte cru dos dois moldes para o menor tamanho):  0.3162
    o metodo de PRODUCAO (`_alinhar_por_preenchimento` + `casamento_da_ancora`):  0.0663

O `0`x`8` reproduziu identico (0,7110) nos dois porque aqueles dois moldes ja tem o MESMO
tamanho — nao havia o que recortar, e a diferenca entre os metodos nao aparecia. O `9` e o `4`
nao tem, e ali recortar em vez de alinhar inventa sobreposicao. **O numero de producao e o
0,0663; o 0,3162 sai de circulacao.** A conclusao nao muda e fica mais forte: o par esta ainda
mais longe do `0`x`8` do que eu havia dito.

Foi a TERCEIRA medicao de improviso do orquestrador a sair torta hoje, depois do harness de
geometria a mao e da hipotese do recorte pela borda. As tres tinham a mesma forma: reimplementar
por fora o que a producao ja faz por dentro. E a razao de esta tarefa ter sido posta DENTRO da
ferramenta.

**Escopo conferido apos o merge:** `git diff --name-only ac23caf HEAD -- l2scanner/` sai VAZIO.
Calibracao intacta — piso 0,4698, margem 0,0370, `mercado_tolerancia_do_cruzamento` ainda `None`,
13 + 13 moldes.
