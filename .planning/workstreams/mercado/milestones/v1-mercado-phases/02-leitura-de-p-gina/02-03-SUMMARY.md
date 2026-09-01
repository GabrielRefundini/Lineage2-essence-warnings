---
phase: 02-leitura-de-p-gina
plan: 03
subsystem: api
tags: [difflib, ocr, agrupamento, similaridade, template-matching, medicao, stdlib]

requires:
  - phase: 02-leitura-de-p-gina
    provides: "a coluna do nome calibrada, a grade de negociacao e as 4 colunas do 02-01"
  - phase: 02-leitura-de-p-gina
    provides: "a sonda de oclusao, o limiar de dispersao e o piso/margem de leitura de glifo do 02-02"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "as 8 gravacoes de campo, os 13 moldes de glifo e as 3 ancoras"
provides:
  - "`l2scanner/mercado_catalogo.py` — os predicados PUROS do agrupamento de nome, sem I/O"
  - "`tools/medir_agrupamento_de_nome.py` — a varredura que PROPOE e grava o corte e o piso"
  - "`mercado_corte_de_similaridade = 0.894737` e `mercado_piso_de_similaridade = 0.883732`, MEDIDOS"
  - "a REFUTACAO da suposicao A8: a assinatura por MOLDE acerta 0 de 10 sob a regra de producao"
  - "o rendimento MEDIDO das TRES rotas do portao de decisao, com series duplicadas"
  - "a UNICA fusao conhecida do corte, nomeada: `B-grade Gemstone` x `C-grade Gemstone`"
  - "4 fixtures versionadas novas em tests/fixtures/mercado/"
affects: [02-04, 02-05, 02-06, agrupamento de nome, catalogo de series, chave da serie]

actuals:
  tokens: 68000
  tasks: 2
  commits: 6

tech-stack:
  added: []
  patterns:
    - "predicado puro com o motor pesado INJETADO, para nao inverter a seta ferramenta->modulo puro antes da promocao"
    - "as DUAS populacoes de uma medicao apoiadas na MESMA nocao de confianca (o acordo entre as duas escalas)"
    - "populacao INDECIDIVEL nomeada e excluida das duas, com o veredito que o corte lhe daria impresso ao lado"
    - "limiar posto no MEIO do vao entre as populacoes, e nao no extremo, quando o extremo tornaria um item permanentemente invisivel"
    - "conferencia da proposta sobre as populacoes INTEIRAS, e nao so sobre os extremos que a produziram"
    - "a lista COMPLETA das fusoes que o corte produz, impressa para leitura humana, porque um corte so se julga junto com o que ele funde"

key-files:
  created:
    - l2scanner/mercado_catalogo.py
    - tools/medir_agrupamento_de_nome.py
    - tests/test_mercado_catalogo.py
    - tests/test_medir_agrupamento_de_nome.py
    - tests/fixtures/mercado/leituras_de_nome.json
    - tests/fixtures/mercado/nome_linha0_f000.png
    - tests/fixtures/mercado/nome_linha0_f010.png
    - tests/fixtures/mercado/nome_sob_tooltip_f015.png
  modified: []

key-decisions:
  - "A trava de digitos e o que torna o corte PROPONIVEL, e isso agora e numero: sem ela as duas populacoes se sobrepoem (vao -0,054416, 182 pares sobrepostos, `+6 Agathion` contra `Agathion` a 0,9492); com ela o vao e +0,022010."
  - "A suposicao A8 esta REFUTADA. Com a posicao do digito dada DE FORA, `assinatura_por_molde` acerta 9 de 9 contra o gabarito. Com a regra que a producao teria de usar — cada run sozinho, digito quando passa no piso e na margem — ela acerta 0 de 10 e devolve `7655` onde a resposta e `6`. Os 13 moldes nao tem CLASSE DE REJEICAO: nao ha molde de letra, entao toda letra e forcada sobre o digito mais parecido."
  - "O piso e o MEIO do vao, e nao `max(precisa separar)`. Com o piso no extremo, o pior par que precisa separar cai exatamente nele e 'empate no piso descarta' tornaria `Wind Spirit Evolution Stone` PERMANENTEMENTE invisivel no catalogo."
  - "A sonda de oclusao do 02-02 filtra a varredura: 951 linhas cobertas de 4.768. Sem esse filtro as populacoes se sobrepunham em 1.338 pares, porque o topo de 'precisa separar' era o MESMO item de uma linha vizinha com a leitura comida pela tooltip."
  - "As duas populacoes se apoiam na MESMA nocao de confianca — o VOCABULARIO DE CONSENSO, os 50 nomes que as duas escalas leram identicos. Sem isso, `'\\ufffdano'` x `'-ano'` (duas leituras falhadas) puxava o corte de 0,8947 para 0,7500."
  - "`assinatura_por_molde` recebe o motor de glifo INJETADO. `segmentar_glifos` e os dois alinhadores moram em `calibrar_mercado.py`, que chama `tornar_consciente_de_dpi()` NO IMPORT; um modulo de producao que o importasse pagaria esse efeito colateral so por existir e inverteria a seta que o repositorio mantem em tres precedentes. A promocao e do 02-04."
  - "A FONTE da assinatura de digitos e o OCR (`ocr-estrito`), escolhida pelo usuario no portao de decisao em 2026-08-30. A `molde` caiu apesar dos 95,32% porque A8 foi refutada (0 de 10 sob a regra de producao) e porque a chave `7655` nao serve um CSV que o usuario quer ler a olho e entregar a outra IA. A `ocr-igualdade` caiu por dominancia estrita."
  - "A `ocr-igualdade` NAO produz as series duplicadas que a hipotese previa: 0 grupos duplicados nas 8 gravacoes, e ela perde 5 linhas a MAIS que a `ocr-estrito` sobre a varredura inteira. O argumento contra ela mudou de 'suja o catalogo' para 'e estritamente dominada'."

patterns-established:
  - "Um rotulo de medicao que a propria medicao refuta e trocado e o motivo fica escrito: este plano trocou o rotulo de 'precisa separar' DUAS vezes, e as duas refutacoes estao na docstring da funcao."
  - "Toda proposta de limiar e conferida contra a populacao INTEIRA antes de ser gravada, e a ferramenta sai com codigo != 0 se a proposta nao se sustentar."
  - "A lista completa do que um corte FUNDE e parte do relatorio, nao um detalhe: um corte so pode ser julgado junto com o que ele custa."

requirements-completed: []

coverage:
  - id: D1
    description: "Os predicados puros do agrupamento existem em `mercado_catalogo.py`: trava de digitos, similaridade por difflib, chave da serie e agrupamento com faixa cinzenta e desempate deterministico"
    requirement: LEIT-01
    verification:
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestATravaDeDigitos"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestASimilaridade"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestAChaveDaSerie"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestOAgrupamento"
        status: pass
    human_judgment: false
  - id: D2
    description: "Nenhuma dependencia nova entra na arvore: a metrica e `difflib` da stdlib e importar o modulo nao puxa `rapidfuzz`"
    requirement: LEIT-01
    verification:
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestOCharterDoModulo::test_importar_o_modulo_nao_puxa_rapidfuzz"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestOCharterDoModulo::test_a_metrica_e_a_da_stdlib"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "O corte e o piso de similaridade foram MEDIDOS por varredura sobre as 8 gravacoes do censo e gravados no calibration.json, e sao reproduziveis num clone limpo sem motor de OCR"
    requirement: LEIT-01
    verification:
      - kind: manual_procedural
        ref: ".venv/Scripts/python.exe tools/medir_agrupamento_de_nome.py --gravacoes <abs>/recordings --calibracao <abs>/calibration.json --gravar (exit 0)"
        status: pass
      - kind: unit
        ref: "tests/test_medir_agrupamento_de_nome.py::TestACorteEOPiso"
        status: pass
    human_judgment: false
  - id: D4
    description: "A suposicao A8 (assinatura de digito por MOLDE) foi medida contra o gabarito de encanto conhecido e REFUTADA sob a regra de producao"
    verification:
      - kind: unit
        ref: "tests/test_medir_agrupamento_de_nome.py::TestARefutacaoDeA8"
        status: pass
      - kind: manual_procedural
        ref: "RELATORIO 3 da varredura: molde[N] 9/9 com a posicao dada de fora, molde[LINHA INTEIRA] 0/10"
        status: pass
    human_judgment: false
  - id: D5
    description: "As TRES rotas do portao de decisao chegaram a mesa com numero medido, inclusive a contagem de series duplicadas projetadas de cada uma"
    verification:
      - kind: manual_procedural
        ref: "RELATORIO 4 da varredura: molde 407/427, ocr-estrito 352/427, ocr-igualdade 351/427; duplicadas 1/0/0"
        status: pass
    human_judgment: false
  - id: D6
    description: "A FONTE da assinatura de digitos da chave da serie foi escolhida pelo usuario com o numero medido na frente: `ocr-estrito`"
    verification:
      - kind: manual_procedural
        ref: "checkpoint:decision gate=blocking-human, 02-03 Task 2 — usuario escolheu `ocr-estrito` com os relatorios 3 e 4 na mesa"
        status: pass
    human_judgment: true
    rationale: "E um `checkpoint:decision` com `gate=\"blocking-human\"` e reversibilidade `one-way`: a chave vai para o disco e a Fase 3 a referencia em cada observacao. Nenhuma automacao pode escolher por ele, e auto-selecao e explicitamente proibida para este gate. RESOLVIDO pelo usuario em 2026-08-30."
  - id: D7
    description: "Nenhuma linha de codigo dos predicados puros esta amarrada a uma fonte de assinatura: `chave_da_serie` e `agrupar` continuam recebendo a assinatura pronta do chamador"
    verification:
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestAChaveDaSerie::test_a_assinatura_entra_na_chave_de_forma_explicita"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_catalogo.py::TestOAgrupamento"
        status: pass
    human_judgment: false

duration: 2h 05m
completed: 2026-08-30
status: complete
---

# Phase 02 Plan 03: Agrupamento de nome — o corte medido e a fonte da assinatura Summary

**Corte 0,894737 e piso 0,883732 medidos por varredura sobre 3.511 linhas limpas das 8 gravacoes, com a trava de digitos provada NECESSARIA (sem ela nao ha corte proponivel), a suposicao A8 REFUTADA (o molde acerta 0 de 10 sob a regra de producao) e a fonte da assinatura decidida pelo usuario: `ocr-estrito`.**

## Performance

- **Duration:** 2h 05m
- **Started:** 2026-08-30T12:55:00Z
- **Completed:** 2026-08-30T15:00:00Z
- **Tasks:** 2 de 2 (a Task 2 foi o portao humano, resolvido)
- **Files modified:** 8 criados, mais 2 chaves no `calibration.json` (gitignored, NAO commitado)

## Accomplishments

- `l2scanner/mercado_catalogo.py` nascido com os cinco predicados puros e nenhuma dependencia nova
- `tools/medir_agrupamento_de_nome.py` produzindo os quatro relatorios sobre o conjunto FECHADO de 8 gravacoes
- Os dois numeros do `calibration.json` MEDIDOS, e reproduziveis num clone limpo a partir da fixture versionada
- A trava de digitos deixou de ser argumento e virou numero: sem ela, nenhum corte e proponivel
- A suposicao A8 (risco ALTO, nunca medida) REFUTADA com o mecanismo da refutacao nomeado
- As TRES rotas do portao com rendimento e series duplicadas medidos sobre a MESMA populacao
- A FONTE da assinatura DECIDIDA pelo usuario com os numeros na mesa: `ocr-estrito`

## Task Commits

1. **Task 1 RED: os predicados afirmados antes de existirem** — `7f118ce` (test)
2. **Task 1 GREEN: os predicados puros do agrupamento** — `ee2822a` (feat)
3. **Task 1: a varredura, as fixtures e o teste de regressao** — `7b5fd46` (feat)
4. **Task 2: a decisao registrada e o caminho de volta** — ver abaixo (docs)

## Files Created/Modified

- `l2scanner/mercado_catalogo.py` — `assinatura_por_ocr`, `assinatura_por_molde`, `similaridade`, `chave_da_serie`, `agrupar`, `ResultadoDoAgrupamento`, `EntradaDoCatalogo`
- `tools/medir_agrupamento_de_nome.py` — a varredura, os quatro relatorios, `--gravar`
- `tests/test_mercado_catalogo.py` — 45 testes sobre os pares medidos da pesquisa
- `tests/test_medir_agrupamento_de_nome.py` — 43 testes sobre as fixtures versionadas
- `tests/fixtures/mercado/leituras_de_nome.json` — as 3.511 linhas lidas 2x/3x
- `tests/fixtures/mercado/nome_linha0_f000.png` — `+6 Agathion Alpha Hunter Sealed`
- `tests/fixtures/mercado/nome_linha0_f010.png` — `Earth Spirit Evolution Stone`
- `tests/fixtures/mercado/nome_sob_tooltip_f015.png` — o vazamento de tooltip medido

---

# OS QUATRO RELATORIOS

Varredura de 2026-08-30, `.venv/Scripts/python.exe`, checkout principal, caminhos absolutos.
As 8 gravacoes do censo; as outras 8 pastas de `recordings/` ignoradas e nomeadas com o motivo.

**O material:** 478 frames com painel aberto. **951 linhas COBERTAS** foram descartadas pela sonda
de oclusao do 02-02 (dispersao > 0,026377), 304 linhas vazias, 2 linhas em que so uma escala leu,
0 linhas que a sonda nao conseguiu medir. **Sobraram 3.511 linhas limpas**, lidas pelas duas
escalas, em 415 frames.

## RELATORIO 1 — o histograma e a proposta

**VOCABULARIO DE CONSENSO: 50 nomes distintos** que as DUAS escalas leram identicos em alguma
linha limpa. E a nocao de leitura confiavel usada dos DOIS lados da medicao.

| populacao | com a trava | SEM a trava |
|---|---|---|
| PRECISAM AGRUPAR (n) | 2.663 | 2.663 |
| min(agrupar) | **0,894737** | 0,894737 |
| PRECISAM SEPARAR (n) | 1.507 | 1.915 |
| max(separar) | **0,872727** | 0,949153 |
| **vao** | **+0,022010** | **−0,054416** |
| pares sobrepostos | **0** | **182** |
| veredito | corte proponivel | **NENHUM corte proponivel** |

**A trava de digitos e o que torna o corte proponivel, e agora isso e numero.** Sem ela o topo de
"precisa separar" e `'+6 Agathion Alpha Hunter Sealed'` contra `'Agathion Alpha Hunter Sealed'` a
**0,9492** — acima do pior par que precisa agrupar. Nenhum escalar decide os dois.

```
mercado_corte_de_similaridade = 0.894737   (empate no corte AGRUPA)
mercado_piso_de_similaridade  = 0.883732   (empate no piso DESCARTA)
FAIXA CINZENTA [0,883732, 0,894737)
```

- **O pior par que o corte tem de aceitar:** `'Common Valakas Chll'` x `'Common Valakas Doll'`,
  **0,8947** (`053105-mercado-aberto/frame_000207:7`)
- **O melhor par que tem de ficar sob o piso:** `'Earth Spirit Evolution Stone'` x
  `'Fire Spirit Evolution Stone'`, **0,8727** (`060622-mercado-pagina-cheia/frame_000013:0x4`)
- **Conferencia sobre as populacoes INTEIRAS:** 0 de 2.663 "precisa agrupar" abaixo do corte;
  0 de 1.507 "precisa separar" no piso ou acima.

**A UNICA fusao que o corte produz, sobre os 50 nomes confirmados:**

| score | a | b |
|---|---|---|
| **0,9375** | `B-grade Gemstone` | `C-grade Gemstone` |

Um caractere, e a trava de digitos nao alcanca: a diferenca e uma LETRA de grade e as duas
assinaturas sao vazias. **E a janela quebrada conhecida deste corte** — registrada em
`WINDOWS.md` e presa por teste (`test_o_corte_funde_EXATAMENTE_um_par_do_vocabulario_confirmado`).
Subir o corte para 0,94 elimina a fusao e leva junto pares que precisam agrupar.

## RELATORIO 2 — o censo do conflito entre as escalas (D-02 x D-03)

**311 de 3.511 linhas (8,86%)** tem assinaturas de digito DIFERENTES entre 2x e 3x. Cada uma
delas MORRE na rota `ocr-estrito`.

O conflito e sempre o mesmo: assinatura `''` contra `'1'`.

```
053105-mercado-aberto/frame_000066.png: 10 de 10 linhas
  2x="Aden's Soul Crystal Lv. I - Armor"
  3x="Aden's Soul Crystal Lv. 1 - Armor"
```

**A perda de PAGINA INTEIRA se confirmou na varredura completa**, e nao so no
`scroll-transicao/frame_000016` que a pesquisa nomeou: ha frames em `053105-mercado-aberto` em que
as 10 de 10 linhas caem.

## RELATORIO 3 — a fonte da assinatura, MEDIDA (a suposicao A8)

Gabarito conhecido de `20260828-063752-mercado-aberto/frame_000000` (o frame que o usuario
calibrou): `+6 / +4 / +2 / +7 / (nenhum) / +5 / +7 / +5 / +7 / +6`.

| linha | gabarito | molde[+N] | molde[N] | molde[LINHA INTEIRA] | OCR |
|---|---|---|---|---|---|
| 0 | `6` | `46` | `6` | `7655` | `6` |
| 1 | `4` | `44` | `4` | `7455` | `4` |
| 2 | `2` | `42` | `2` | `7255` | `2` |
| 3 | `7` | `47` | `7` | `7755` | `7` |
| 4 | (nenhum) | `None` | `5` | `55` | (nenhum) |
| 5 | `5` | `45` | `5` | `7555` | `5` |
| 6 | `7` | `47` | `7` | `7755` | `7` |
| 7 | `5` | `45` | `5` | `7555` | `5` |
| 8 | `7` | `47` | `7` | `7755` | `7` |
| 9 | `6` | `46` | `6` | `7655` | `6` |

- **MOLDE[N]** (digito isolado, **com a posicao dada DE FORA**): **9 acerto, 0 descarte, 0 erro**
- **MOLDE[LINHA INTEIRA]** (a regra que a producao teria de usar): **0 acerto, 10 erro**
- **OCR**: **9 acerto, 0 erro**

**O mecanismo da refutacao, nomeado.** Os 13 moldes **nao tem classe de rejeicao** — nao ha molde
de letra, entao toda letra e forcada sobre o digito mais parecido e algumas passam no piso. Sobre
60 paginas distintas e 427 linhas:

| populacao | n | min | mediana | max |
|---|---|---|---|---|
| **VERDADEIRO** (o digito de um `+N `) | 28 | **0,8510** | 0,9169 | 0,9439 |
| **FALSO** (todo run aprovado num nome sem digito nenhum) | 451 | 0,4752 | 0,5918 | **0,6947** |

**HA VAO** (+0,1563) — mas ele exigiria um piso NOVO, proprio da coluna do nome. **O piso que este
projeto tem hoje (0,4698, medido sobre colunas de NUMERO) nao separa**, e por isso a linha 0 sai
como `7655`. Os falsos positivos sao concretos: `run #25 lido como '5' em 'Agathion Alpha Hunter
Sealed'`, `run #12 lido como '5' em 'Common Samurai Doll'`.

**E ha um segundo achado mecanico.** O digito so casa quando isolado: a faixa de linhas que
`segmentar_glifos` compartilha entre todos os runs do nome e esticada pelas ASCENDENTES DAS
LETRAS (11 px medidos), e um digito medido dentro dela nao casa com um molde cortado de uma coluna
que so tem digito — o score do `+6` sobe de **0,31 para 0,89** quando o recorte e so dele.

**O caso `Lv. N`** — o digito no MEIO do nome, e nao no prefixo:

```
053105-mercado-aberto/frame_000066:0
  2x="Aden's Soul Crystal Lv. I - Armor"  ->  assinatura ''
  3x="Aden's Soul Crystal Lv. 1 - Armor"  ->  assinatura '1'
  molde[ultimo run]=None       molde[LINHA INTEIRA]='5'
```

O molde **nao le o `1`** em caso nenhum. A rota `molde` nao resolve o `Lv. N` lendo o digito; ela o
resolve por acidente, porque a assinatura sai dos PIXELS e por isso e identica para as duas escalas.

## RELATORIO 4 — o rendimento das TRES rotas

As tres comparadas sobre as MESMAS 427 linhas das 60 paginas distintas (a rota `molde` custa 13
casamentos por run e nao roda sobre as repeticoes; comparar rotas sobre populacoes diferentes nao
compara nada).

| rota | li | perdi | taxa | series | duplicadas |
|---|---|---|---|---|---|
| **molde** | **407** | **20** | **95,32%** | 47 | **1 grupo, 1 serie a mais** |
| **ocr-estrito** | 352 | 75 | 82,44% | 42 | **0** |
| **ocr-igualdade** | 351 | 76 | 82,20% | 41 | **0** |

Sobre a varredura INTEIRA (3.511 linhas), para conferencia — a rota `molde` nao entra aqui:

| rota | li | perdi | taxa | series |
|---|---|---|---|---|
| ocr-estrito | 2.993 | 518 | 85,25% | 55 |
| ocr-igualdade | 2.988 | 523 | 85,10% | 54 |

**A serie duplicada da rota `molde`** e a assinatura instavel em acao:

```
adena#55    'Adena'
adena#555   'Adena'
```

O mesmo item, com a "assinatura" mudando conforme quais letras passaram no piso naquele frame.

**A `ocr-igualdade` NAO produziu as series duplicadas que a hipotese previa: ZERO.** Ela recusa a
linha antes de criar a serie duplicada, entao o lixo previsto nao aparece — e em troca ela perde 5
linhas a mais que a `ocr-estrito` sobre a varredura inteira e cria uma serie a menos. Ela e
**estritamente dominada** pela `ocr-estrito` neste material. O argumento contra ela mudou, e o
numero e que mudou.

---

# TASK 2 — A DECISAO DO PORTAO

**FONTE ESCOLHIDA: `ocr-estrito`.** A sequencia de digitos da chave da serie vem do **OCR**, e
a linha cai quando as duas escalas discordam no digito. Escolhida pelo usuario em 2026-08-30,
no `checkpoint:decision` de `gate="blocking-human"`, com os relatorios 3 e 4 na frente.

## Por que ela, e o que caiu junto

**`molde` — RECUSADA, apesar de ler 95,32% contra 82,44%.**
O motivo e a propria medicao desta wave: com a regra que a producao teria de usar, ela acerta
**0 de 10** contra o gabarito de encanto. Os 13 moldes sao `0`-`9`, `,`, `XM Coin` e `Adena` —
**nao ha molde de letra**, entao o conjunto nao tem classe de rejeicao e toda letra e forcada
sobre o digito mais parecido. O que sai nao e sequencia de digitos: e impressao digital do nome,
e ela varia com o frame (o `Adena` duplicou em `adena#55` e `adena#555`). E ha um custo que nao
aparece em taxa nenhuma: **a chave vai para um CSV que o usuario quer ler a olho nu e entregar a
outra IA analisar** — `7655` nao serve nenhum dos dois usos. Os 13 pontos percentuais a mais
seriam pagos com uma chave que ninguem consegue interpretar.

**`ocr-igualdade` — RECUSADA por DOMINANCIA ESTRITA.**
Le 351 contra 352 (2.988 contra 2.993 na varredura inteira), cria uma serie a menos, e **nao
resgata o `Lv. I`/`Lv. 1`**, que era a razao inteira de ela existir: quando as escalas discordam
a linha morre igual. A hipotese contra ela — que criaria series duplicadas — **nao se
confirmou**: zero duplicatas nas 8 gravacoes, porque ela recusa a linha antes de duplicar. Mas
isso nao a salvou; recusar antes de duplicar e o que a `ocr-estrito` ja faz, e melhor. Ela nao
tem nenhuma dimensao em que ganhe.

**`ocr-estrito` — ESCOLHIDA, com o custo aceito de olhos abertos.**
D-03 fica literal, sem mecanismo novo. Fusao por digito e impossivel por construcao. Zero series
duplicadas. **O preco, que o usuario conhece:** 311 de 3.511 linhas limpas (**8,86%**) morrem
porque as escalas discordam no digito, e ha frames em `053105-mercado-aberto` onde sao **10 de
10** — pagina inteira. Os `Aden's` e `Hardin's Soul Crystal Lv. N` ficam permanentemente
ilegiveis. Isso derruba, na pratica, o exemplo que D-02 citava como "o ruido que o agrupamento
tem de absorver": a trava de digitos chega primeiro. A ressalva esta anotada no `02-CONTEXT.md`,
no bullet onde a promessa foi feita.

## O caminho de volta, com os dois numeros

**A rota `molde` nao e impossivel — ela e INCOMPLETA, e falta exatamente UM numero.** Medido na
mesma varredura, sobre 60 paginas distintas e 427 linhas da coluna do nome, com cada run
reclassificado na propria faixa:

| populacao | n | min | max |
|---|---|---|---|
| VERDADEIRO — o digito de um prefixo `+N ` | 28 | **0,8510** | 0,9439 |
| FALSO — todo run aprovado num nome sem digito nenhum | 451 | 0,4752 | **0,6947** |

**Vao de +0,1563.** Um piso PROPRIO da coluna do nome, medido nessa faixa (chave nova, algo como
`mercado_limiar_de_digito_no_nome`), separaria digito de letra e devolveria os 95,32% com chave
honesta. O piso de hoje (`mercado_limiar_de_leitura_de_glifo` = 0,4698) **nao serve**: foi medido
sobre colunas de NUMERO, onde nao ha letra para rejeitar.

Os dois numeros estao escritos em tres lugares para ninguem ter de remedir:
- a docstring de `l2scanner/mercado_catalogo.assinatura_por_molde` (onde quem revive a rota olha)
- o `<deferred>` do `02-CONTEXT.md`
- aqui

**E trocar a fonte depois e portao de novo:** a chave ja gravada no CSV orfana, e as observacoes
antigas apontam para uma chave que a leitura nova nunca mais produz.

## A porta que ficou aberta de proposito

**`B-grade Gemstone` x `C-grade Gemstone`, 0,9375 — o corte funde os dois.** Um caractere, e e
LETRA de grade: **a trava de digitos nao alcanca**, porque as duas assinaturas sao vazias. E a
UNICA fusao sobre os 50 nomes confirmados, e ela **sobrevive a escolha da fonte** — nenhuma das
tres rotas a evitaria, porque nenhuma delas mexe em letra.

Ficou aberta por medicao, e nao por descuido: subir o corte para 0,94 elimina a fusao **e leva
junto pares que precisam agrupar** (`test_um_corte_mais_alto_nao_resolve_sem_perder_o_que_precisa_agrupar`
prende as duas metades). Registrada em `.planning/WINDOWS.md` como `open` e presa por teste em
`test_o_corte_funde_EXATAMENTE_um_par_do_vocabulario_confirmado`. Quem ler este SUMMARY precisa
saber que ela existe, que e conhecida, e que fechar custa dado.

## O que a decisao NAO mudou no codigo

**Nenhuma linha dos predicados puros foi amarrada a uma fonte.** `chave_da_serie(nome, assinatura)`
e `agrupar(leitura, assinatura, catalogo, corte, piso)` continuam recebendo a assinatura JA
CALCULADA do chamador, exatamente como antes do portao. `assinatura_por_ocr` e
`assinatura_por_molde` continuam as duas no modulo, e a segunda agora carrega no docstring o
numero que a derrubou e o que a devolveria. **Quem escolhe a fonte e o 02-04**, ao fiar
`mercado_pagina.py` — e por isso a decisao pode ser registrada sem reescrever `mercado_catalogo.py`.

---

## Decisions Made

**A decisao do portao: `ocr-estrito`** — ver a secao "TASK 2" acima, com as duas recusadas e o
custo de cada uma.

Ver `key-decisions` no frontmatter. As tres da medicao que mais mudaram o plano:

1. **A sonda de oclusao entrou na varredura** (nao estava no plano). Sem ela as populacoes se
   sobrepunham em 1.338 pares, porque o topo de "precisa separar" era o MESMO item de uma linha
   vizinha com a leitura comida pela tooltip.
2. **O rotulo "precisa separar" foi trocado DUAS vezes por medicao**, e as duas refutacoes ficaram
   escritas na docstring da funcao.
3. **O piso e o MEIO do vao**, e nao o extremo — porque o extremo tornaria um item real
   permanentemente invisivel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] A sonda de oclusao do 02-02 passou a filtrar a varredura**
- **Found during:** Task 1 (a primeira rodada do gate sobre as 8 gravacoes)
- **Issue:** O plano nao pedia o filtro. Sem ele a populacao "precisa separar" ficava contaminada
  por linhas em que a tooltip comeu ou acrescentou pedaco do nome —
  `'Common Mafia der Luciano Doll'` contra `'Common Mafia Leader Luciano Doll'` (0,9508),
  `"Aden's Soul Crystal Lv. 1 - W"` contra `"... - Weapon"` (0,9206) — todas o MESMO item de uma
  linha vizinha. As duas populacoes se sobrepunham em **1.338 pares** e a ferramenta saia com
  codigo 7 sem propor nada. Em producao essas linhas nao chegam ao agrupamento: a sonda as
  descarta antes (D-14). Medir o corte sobre elas seria calibrar sobre uma populacao que a
  producao nunca ve — o mesmo erro que o 02-02 corrigiu ao julgar a guarda de cruzamento sobre a
  populacao pos-piso.
- **Fix:** `varrer` chama `mercado_geometria.nivel_de_fundo_da_linha` com
  `mercado_sonda_do_fundo` e recusa a linha acima de `mercado_limiar_de_dispersao_do_fundo`. As
  duas chaves entraram no portao de carga da ferramenta.
- **Files modified:** `tools/medir_agrupamento_de_nome.py`
- **Verification:** 951 linhas cobertas descartadas; max(separar) caiu de 0,9508 para 0,8923
- **Committed in:** `7b5fd46`

**2. [Rule 1 - Bug] O rotulo "precisa separar" aceitava leitura que so UMA escala produziu**
- **Found during:** Task 1 (a segunda rodada do gate)
- **Issue:** Mesmo com a sonda, o topo continuava sendo o mesmo item corrompido:
  `'Cohi nn Mafia Leader Luciano Doll'` contra `'Common Mafia Leader Luciano Doll'` (0,8923). A
  marcacao de alvo corrompe o INICIO do nome, e a sonda do 02-02 mede um trecho a DIREITA — ela
  nao alcanca esse caso. Uma leitura que so uma escala produziu nao autoriza ninguem a dizer
  "estes sao dois itens diferentes".
- **Fix:** So linhas em que as duas escalas concordam exatamente entram em "precisa separar". O
  topo passou a ser `'Water Spirit Evolution Stone'` x `'Wind Spirit Evolution Stone'` (0,8727),
  que sao mesmo dois itens diferentes.
- **Files modified:** `tools/medir_agrupamento_de_nome.py`
- **Verification:** `test_precisa_separar_so_aceita_linha_de_CONSENSO`
- **Committed in:** `7b5fd46`

**3. [Rule 1 - Bug] Duas leituras FALHADAS puxavam o corte para baixo**
- **Found during:** Task 1 (a terceira rodada)
- **Issue:** `'�ano'` x `'-ano'` — quatro caracteres, o resto do nome comido — entrava em
  "precisa agrupar" e sozinho puxava o corte de 0,8947 para **0,7500**. Um par assim nao e uma
  leitura ruidosa de um NOME: sao duas leituras falhadas.
- **Fix:** "Precisa agrupar" exige que ao menos um dos dois lados esteja no VOCABULARIO DE
  CONSENSO. Os 368 pares excluidos sao impressos com o veredito que o corte lhes daria: 367
  agrupariam mesmo assim, 1 nao (justamente o `-ano`).
- **Files modified:** `tools/medir_agrupamento_de_nome.py`
- **Verification:** `test_precisa_agrupar_exclui_o_par_em_que_os_DOIS_lados_falharam`
- **Committed in:** `7b5fd46`

**4. [Rule 1 - Bug] O piso no extremo tornava um item real permanentemente invisivel**
- **Found during:** Task 1 (ao conferir a proposta)
- **Issue:** `piso = max(precisa separar)` punha o pior par exatamente NO piso, e "empate no piso
  descarta" — entao `'Wind Spirit Evolution Stone'` (0,8727 contra `'Water Spirit ...'`) seria
  descartado toda vez, em vez de virar serie nova. Descarte nao e irreversivel quando acontece uma
  vez; e irreversivel quando acontece SEMPRE para o mesmo item.
- **Fix:** `piso = (max(separar) + corte) / 2`, a mesma construcao de `mercado_limiar_de_glifo`.
- **Files modified:** `tools/medir_agrupamento_de_nome.py`
- **Verification:** `test_o_piso_e_o_MEIO_do_vao_e_nao_o_maximo_de_separar`
- **Committed in:** `7b5fd46`

**5. [Rule 1 - Bug] O criterio de "serie duplicada" punia as rotas por acertarem**
- **Found during:** Task 1 (RELATORIO 4)
- **Issue:** O criterio inicial (similaridade acima do corte ignorando a trava) acusava
  `+2 Agathion Alpha Hunter Sealed` e `+4 Agathion ...` como duplicata um do outro. Sao itens
  DIFERENTES: a trava existe justamente para separa-los.
- **Fix:** Duas series sao a mesma quando as grafias colapsam ao desfazer as confusoes conhecidas
  do motor (`I/1`, `O/0`, `S/5`, `B/8`, `l/1`, caixa). `Lv. I` e `Lv. 1` colapsam; `Lv. 1` e
  `Lv. 3` nao.
- **Files modified:** `tools/medir_agrupamento_de_nome.py`
- **Verification:** `TestAsSeriesDuplicadas` (4 testes)
- **Committed in:** `7b5fd46`

**6. [Rule 3 - Blocking] `assinatura_por_molde` recebe o motor de glifo INJETADO**
- **Found during:** Task 1 (ao escrever o modulo)
- **Issue:** A assinatura do plano era `assinatura_por_molde(recorte_bgr, moldes, piso, margem)`,
  usando `segmentar_glifos`. Mas essa funcao e os dois alinhadores moram em `calibrar_mercado.py`,
  que **chama `tornar_consciente_de_dpi()` no import** e carrega `argparse`/`cv2.imshow`. Um
  modulo de PRODUCAO que o importasse pagaria esse efeito colateral so por existir, e inverteria a
  seta que o repositorio mantem em tres precedentes (`grep "import calibrar_mercado"
  l2scanner/*.py` -> vazio). A promocao dessas primitivas e do 02-04, que declara
  `calibrar_mercado.py` em `files_modified`; faze-la aqui tocaria arquivos que este plano nao
  declarou.
- **Fix:** `pontuar_runs` chega por argumento nomeado obrigatorio, no mesmo desenho de
  `VigiaDeManutencao.__init__` (injecao de leitora, nao monkeypatch). A ferramenta, que E
  ferramenta, e quem importa de `calibrar_mercado`.
- **Files modified:** `l2scanner/mercado_catalogo.py`
- **Verification:** `test_o_modulo_puro_nao_importa_a_ferramenta_de_calibracao`
- **Committed in:** `ee2822a`

**7. [Rule 1 - Bug] O criterio de aceite do plano citava um numero de outro par**
- **Found during:** Task 1 (fase RED)
- **Issue:** O criterio dizia "`Evolution`x`Ewlution` acima de 0,90". As palavras SOLTAS dao
  **0,8235**. O 94,55 da pesquisa e do NOME INTEIRO (`Earth Spirit Evolution Stone` x
  `Earth Spirit Ewlution Stone` = 0,9455), que e o que a producao compara.
- **Fix:** O teste cobra o par de nome inteiro acima de 0,90 E prende a palavra solta abaixo de
  0,90, com a distincao escrita — para que ninguem "conserte" o corte por causa de uma comparacao
  que nunca acontece.
- **Files modified:** `tests/test_mercado_catalogo.py`
- **Verification:** `test_a_palavra_solta_NAO_chega_a_090_e_isso_esta_registrado`
- **Committed in:** `ee2822a`

**8. [Rule 1 - Bug] Tres asserções minhas sobre a fixture do tooltip estavam erradas**
- **Found during:** Task 1 (primeira rodada de `test_medir_agrupamento_de_nome.py`)
- **Issue:** Eu supus que a tooltip ACRESCENTARIA glifo. MEDIDO: a mascara de brilho ve **152**
  pixels de texto na linha coberta contra **213** na limpa, e **24 runs contra 28**. A tooltip e
  SEMITRANSPARENTE: ela MISTURA o nome e o derruba abaixo do corte de brilho. (E supus tambem que
  `D-grade Crystal`/`D-grade crystal` virariam duas series; o slug ja e minusculo e elas colidem
  na propria chave.)
- **Fix:** Os testes afirmam o que foi medido, com a suposicao derrubada registrada na docstring.
- **Files modified:** `tests/test_medir_agrupamento_de_nome.py`
- **Verification:** `TestOVazamentoDaTooltip` (4 testes)
- **Committed in:** `7b5fd46`

---

**Total deviations:** 8 auto-fixed (5 bugs, 1 missing critical, 1 blocking, 1 criterio corrigido)
**Impact on plan:** Nenhum scope creep. Sete dos oito sao a propria medicao corrigindo o rotulo
que eu tinha dado a ela — sem eles a ferramenta nao propunha corte nenhum, ou propunha um corte
que se apoiava em leitura falhada. O oitavo e estrutural e preserva a seta ferramenta -> modulo puro.

## Known Stubs

Nenhum stub. Os dois numeros estao gravados e reproduziveis; nenhum caminho de codigo devolve
valor de mentira.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: spoofing (T-02-11, agravado) | `tools/medir_agrupamento_de_nome.py` | A sonda de fundo do 02-02 mede um trecho a DIREITA do inicio do nome (`x` em `[207, 417)` a partir de `gx`). A marcacao de alvo corrompe o INICIO — medido em `061409-mercado-alvo-sobreposto/frame_000012:7`, `'Cohi nn Mafia Leader Luciano Doll'` passou pela sonda como linha limpa. O 02-04, que poe a sonda no pipeline, precisa saber que a cobertura dela NAO cobre a coluna do nome inteira. |

## Issues Encountered

- **A varredura demora.** 478 frames x 10 linhas x 2 escalas de OCR sao ~9.500 chamadas ao motor
  do Windows. Cada rodada do gate custa alguns minutos, e foram quatro rodadas ate o rotulo das
  populacoes parar de ser refutado. O despejo `--despejar-leituras` existe por causa disso: com a
  fixture no disco, a analise inteira roda em 2 segundos sem OCR nenhum.
- **O flake conhecido do `tests/test_agenda.py` nao apareceu** nesta arvore hoje. Suite medida
  separada mesmo assim, pela orientacao ja registrada.

## Next Phase Readiness

**O portao fechou: a fonte e `ocr-estrito`.** O 02-04 ja tem o que precisava para fiar
`mercado_pagina.py`.

Prontos para o 02-04:
- os cinco predicados puros, presos por 45 testes, **nenhum amarrado a uma fonte** —
  `chave_da_serie` e `agrupar` recebem a assinatura pronta do chamador
- **a fonte decidida:** o chamador passa `assinatura_por_ocr(texto)` de cada escala, e a linha
  cai quando as duas assinaturas diferem
- `mercado_corte_de_similaridade = 0,894737` e `mercado_piso_de_similaridade = 0,883732` no
  `calibration.json`
- o aviso de que a promocao de `segmentar_glifos` para `mercado_leitura.py` deixa
  `assinatura_por_molde` livre da injecao
- o `threat_flag` sobre o alcance da sonda de fundo: ela mede a DIREITA do inicio do nome e nao
  pega a marcacao de alvo sobre o comeco
- **as duas janelas abertas de proposito**, em `WINDOWS.md`: a fusao
  `B-grade Gemstone` x `C-grade Gemstone` e o alcance da sonda

Espera-se do 02-04, sem surpresa: **8,86% das linhas caindo** por desacordo de digito entre as
escalas, com pagina inteira em alguns frames. E o custo aceito, e o console tem de mostra-lo como
"li N, perdi M" em vez de escondê-lo.

## Self-Check: PASSED

Arquivos criados, conferidos no disco:

```
FOUND: l2scanner/mercado_catalogo.py
FOUND: tools/medir_agrupamento_de_nome.py
FOUND: tests/test_mercado_catalogo.py
FOUND: tests/test_medir_agrupamento_de_nome.py
FOUND: tests/fixtures/mercado/leituras_de_nome.json
FOUND: tests/fixtures/mercado/nome_linha0_f000.png
FOUND: tests/fixtures/mercado/nome_linha0_f010.png
FOUND: tests/fixtures/mercado/nome_sob_tooltip_f015.png
```

Commits, conferidos no `git log`:

```
FOUND: 7f118ce  test(02-03) RED
FOUND: ee2822a  feat(02-03) GREEN
FOUND: 7b5fd46  feat(02-03) varredura + fixtures
```

Verificacao do plano:

```
python -m pytest tests/test_mercado_catalogo.py tests/test_medir_agrupamento_de_nome.py -q
    88 passed
python -m pytest tests/test_firewall_escopo.py -q
    18 passed
python -c "import sys, l2scanner.mercado_catalogo; assert 'rapidfuzz' not in sys.modules; ..."
    sem rapidfuzz ok
python -c "import inspect, l2scanner.mercado_catalogo as m; assert 'SequenceMatcher' in ..."
    difflib ok
Suite completa (sem test_agenda.py):  1922 passed, 2 skipped
tests/test_agenda.py sozinho:          132 passed
Gate da varredura (checkout principal, .venv, caminhos absolutos):  exit 0
calibration.json:  13 moldes, 3 ancoras, versao 2, layout negociacao, 40 chaves — INTACTO
```

`calibration.json` NAO foi commitado (gitignored, conferido com `git check-ignore`).

Depois do fechamento da Task 2 (a decisao, a anotacao no `02-CONTEXT.md` e o caminho de volta na
docstring), a suite foi rodada de novo, com o mesmo resultado:

```
python -m pytest -q --ignore=tests/test_agenda.py   1922 passed, 2 skipped
python -m pytest tests/test_agenda.py -q             132 passed
python -m pytest tests/test_firewall_escopo.py -q     18 passed
sem rapidfuzz ok / difflib ok
```

E a invariante que a Task 2 exigia, conferida: **`chave_da_serie` e `agrupar` continuam recebendo
a assinatura pronta do chamador.** Nenhum dos dois chama `assinatura_por_ocr` nem
`assinatura_por_molde`; a fonte e escolha de quem chama, e por isso a decisao do usuario pode ser
registrada sem reescrever uma linha dos predicados.

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-30 (portao da Task 2 resolvido: `ocr-estrito`)*
