---
phase: 02-leitura-de-p-gina
plan: 06
subsystem: api
tags: [opencv, numpy, template-matching, guarda-de-cruzamento, falha-fechada, aritmetica-inteira]

requires:
  - phase: 02-leitura-de-p-gina
    provides: "o veredito DECIDIVEL da guarda de cruzamento e a tolerancia gravada como None (02-02)"
  - phase: 02-leitura-de-p-gina
    provides: "`ler_linha`, `ler_celula_de_numero`, `LinhaLida`, `Descarte` e o pipeline de peneiras (02-04)"
  - phase: 02-leitura-de-p-gina
    provides: "a chave `mercado_coluna_do_unitario`, marcada pela mao do usuario no portao humano (02-01)"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "o caso conhecido `40,00` x 48 exibido como `0,83` (SPIKE-RESPOSTAS secao 4)"
provides:
  - "a TERCEIRA leitura de numero: `ler_linha` recorta e le `mercado_coluna_do_unitario`"
  - "`residuo_do_cruzamento` e `cruzamento_confere` em producao, aritmetica INTEIRA de centesimos"
  - "`LinhaLida.residuo_do_cruzamento` — a observacao da Fase 2 sobre a propria leitura"
  - "`MOTIVO_DO_CRUZAMENTO`, o quinto motivo de recusa, distinguivel dos outros quatro"
  - "a refutacao da guarda ESCRITA NO FONTE, com o veredito do 02-02 transcrito literal"
  - "a PROMOCAO da aritmetica do cruzamento de `tools/medir_leitura_de_glifo.py` para producao"
affects: [02-07, Fase 3, Fase 4, CSV de observacoes]

actuals:
  tokens: 46833
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns:
    - "guarda REPROVADA que degrada para OBSERVACAO em vez de sumir: o residuo continua calculado, guardado e logado, e a refutacao fica ao lado da funcao"
    - "o mecanismo caro provado pela CONTAGEM sobre fixtura conhecida (linhas com residuo nao nulo == linhas lidas), e nao pela existencia da funcao"
    - "substituicao `0`x`8` injetada com PIXEL DE VERDADE do mesmo frame e da mesma linha, com uma afirmacao separada de que a injecao landou"
    - "tolerancia como parametro obrigatorio SEM valor de fabrica, com a derivacao no comentario para tornar o medido conferivel"
    - "bateria DUPLA e assimetrica: a rota de producao (guarda OFF) e a rota de ensaio (tolerancia derivada), para o mecanismo estar provado no dia em que uma medicao futura o aprovar"

key-files:
  created: []
  modified:
    - l2scanner/mercado_leitura.py
    - l2scanner/mercado_pagina.py
    - tools/medir_leitura_de_glifo.py
    - tests/test_mercado_leitura.py
    - tests/test_mercado_pagina.py

key-decisions:
  - "A rota executada foi a REPROVADA. O 02-02 emitiu `GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)`, com fechamento no limite derivado 0,6525 e deteccao 0,0164 sobre 1.893 substituicoes injetadas. A guarda NAO descarta nada; o residuo vira observacao."
  - "A guarda entra DEPOIS das tres celulas e da gramatica, e ANTES do OCR. Uma linha que ela derruba nunca vira dado, entao pagar ~7 ms de OCR por ela seria pagar por nada — a mesma razao ja escrita para as colunas de numero. Preso por teste: o descarte do cruzamento faz ZERO chamadas de OCR."
  - "O unitario ilegivel, a quantidade zero e a tolerancia nula devolvem `None` (`nao opino`), e `None` NUNCA vira descarte. Falha fechada e sobre o DADO ilegivel, jamais sobre a ausencia de uma segunda opiniao."
  - "MEDIDO NAS FIXTURAS, e novo: o cliente parece TRUNCAR o unitario, e nao arredondar. Em `janela_negociacao_f005.png` linha 5 a tela mostra `11,39` por 6 com unitario `1,89`, mas `1139/6 = 1,8983` arredondaria para `1,90`. O residuo ali e 5 contra limite derivado 3 — mais uma explicacao para o fechamento de 0,6525 que reprovou a guarda."
  - "A aritmetica do cruzamento foi PROMOVIDA da ferramenta para producao em vez de copiada. Manter duas copias deixaria o scanner e a varredura medindo coisas ligeiramente diferentes no dia em que uma delas fosse corrigida."

patterns-established:
  - "Refutacao no fonte com o VEREDITO LITERAL transcrito (`1273.0000 centesimos por unidade`), preso por teste de inspecao de fonte, para que uma releitura futura saiba que a guarda esta desligada por medicao e nao por esquecimento"
  - "Observacao logada so quando ha o que dizer (residuo acima do limite DERIVADO), e calada quando a guarda esta ligada, para nao haver dois registros do mesmo evento"

requirements-completed: [LEIT-02]

coverage:
  - id: D1
    description: "A TERCEIRA leitura acontece: `ler_linha` recorta `mercado_coluna_do_unitario` e a le com a mesma `ler_celula_de_numero` das outras duas colunas"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestATerceiraLeituraACONTECE::test_toda_LinhaLida_de_f010_carrega_residuo_do_cruzamento"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestATerceiraLeituraACONTECE::test_toda_LinhaLida_de_f005_carrega_residuo_do_cruzamento"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestATerceiraLeituraACONTECE::test_o_unitario_da_fixtura_de_glifos_le_600"
        status: pass
    human_judgment: false
  - id: D2
    description: "`residuo_do_cruzamento` e `cruzamento_confere` em aritmetica INTEIRA de centesimos, com `tolerancia` obrigatoria e sem valor de fabrica"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestOResiduoDoCruzamento"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestCruzamentoConfere"
        status: pass
      - kind: other
        ref: "python -c \"import l2scanner.mercado_leitura as m, inspect; sig=inspect.signature(m.cruzamento_confere); assert sig.parameters['tolerancia'].default is inspect.Parameter.empty\" -> 'sem default ok'"
        status: pass
    human_judgment: false
  - id: D3
    description: "A rota REPROVADA: a guarda nao descarta nada, o residuo e calculado, guardado em `LinhaLida` e logado, e a refutacao fica escrita no fonte com os numeros"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestARotaREPROVADA"
        status: pass
      - kind: other
        ref: "python -c \"import l2scanner.mercado_leitura as m, dataclasses as d; assert 'residuo_do_cruzamento' in {f.name for f in d.fields(m.LinhaLida)}\" -> 'campo ok'"
        status: pass
    human_judgment: false
  - id: D4
    description: "A rota APROVADA, exercitada com a tolerancia DERIVADA: a substituicao `0` por `8` vira `Descarte` com motivo proprio, sem pagar OCR"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestARotaAPROVADA"
        status: pass
    human_judgment: false
  - id: D5
    description: "Se o residuo vai para o CSV e decisao da Fase 3 — a Fase 2 nao mexe na fronteira"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestAFronteiraDaFase3"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-30
status: complete
---

# Phase 02 Plano 06: A guarda de cruzamento Summary

**A terceira coluna de numero passou a ser LIDA e conferida contra o `Total` — e a guarda que ela alimenta ficou DESLIGADA por medicao, degradada para observacao, com o veredito do 02-02 transcrito literal no fonte**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-30T16:55:00Z (aprox. — inicio da leitura do plano)
- **Completed:** 2026-08-30T17:20:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## O VEREDITO DO 02-02, TRANSCRITO, E A ROTA EXECUTADA

O `02-02-SUMMARY.md` emitiu, no formato fixo que este plano le literalmente:

```
GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)
```

| criterio | exigido | medido | veredito |
|---|---|---|---|
| fechamento | >= 0,99 | 0,9992 — **so com tolerancia 1273** | — |
| tolerancia | <= 1,0 centesimo por unidade | **1273,0** | **CAIU** |
| deteccao | >= 0,90 | **0,0164** sobre 1.893 substituicoes `0`<->`8` | tambem cairia |

Fechamento no LIMITE DERIVADO (0,5 por unidade): **0,6525**.

**Rota executada: a REPROVADA.** `mercado_tolerancia_do_cruzamento` continua `None`, a guarda
**nao descarta nada em nenhuma circunstancia**, e o mecanismo degradou para OBSERVACAO — o residuo
e calculado, guardado em `LinhaLida.residuo_do_cruzamento` e registrado no log. A refutacao entrou
no fonte ao lado da funcao, no padrao de `ocr.py:34-52`, com os tres numeros e o criterio que caiu.

## A CONTAGEM QUE PROVA A TERCEIRA LEITURA

O criterio central desta task nao e a guarda: e a leitura que a alimenta. Sem o recorte de
`mercado_coluna_do_unitario` o unitario chegaria `None` em toda linha, `cruzamento_confere`
responderia "nao opino" sempre, e **todos os outros criterios ficariam verdes sobre codigo morto**
(T-02-39). Medido sobre as duas fixturas de pagina, com `LeitorDePagina` inteiro:

```
janela_negociacao_f010.png:  LinhaLida = 2   com residuo NAO nulo = 2   residuos = [(6, 0), (8, 0)]
janela_negociacao_f005.png:  LinhaLida = 4   com residuo NAO nulo = 4   residuos = [(1, 0), (3, 0), (5, 5), (6, 0)]
```

**Igualdade ESTRITA nas duas fixturas, e maior que zero nas duas.** O relaxamento que o plano
autorizava ("maior ou igual a 1 E igual ao numero de linhas com total e quantidade lidos") NAO foi
necessario: toda linha que le total e quantidade tambem le o unitario nestes dois frames.

E a fixtura de glifo confirma o gabarito independente: `glifos_unitario_f010.png` le **600
centesimos**, conferindo com o `6,00` que o cabecalho de `tests/test_mercado_glifos.py` ja
declarava antes deste plano.

## Accomplishments

- **A terceira leitura existe e e CHAMADA.** `ler_linha` recorta `mercado_coluna_do_unitario` e a
  le com a MESMA `ler_celula_de_numero`, com o mesmo piso e a mesma margem das outras duas colunas.
  Esta e a unica consumidora da chave que o portao humano do 02-01 cobrou da mao do usuario.
- **`residuo_do_cruzamento` e `cruzamento_confere` em producao**, em aritmetica INTEIRA de
  centesimos, sem uma unica divisao (T-02-38). `tolerancia` e parametro obrigatorio, sem valor de
  fabrica.
- **`LinhaLida.residuo_do_cruzamento`**, com a docstring dizendo explicitamente que se ele vai para
  o CSV e decisao da FASE 3 — a fronteira nao se mexeu aqui.
- **Um quinto motivo de recusa (`cruzamento`)**, distinguivel dos quatro anteriores, porque o
  usuario precisa ler no log qual peneira pegou o que (D-17).
- **A refutacao escrita no fonte**, com o veredito literal do 02-02, a tabela dos tres criterios e
  a explicacao estrutural (o portao de LAYOUT so nasceu no 02-04, depois da varredura).
- **A aritmetica do cruzamento PROMOVIDA** de `tools/medir_leitura_de_glifo.py` para producao, em
  vez de duplicada.

## Task Commits

1. **Task 1 (RED): a guarda e a terceira leitura, afirmadas antes de existirem** — `d20373d` (test)
2. **Task 1 (GREEN): a terceira leitura e a guarda, com a refutacao no fonte** — `af4635b` (feat)

_Sem commit de REFACTOR: `ruff check` passou limpo no primeiro GREEN e nao havia o que limpar._

## Files Created/Modified

- `l2scanner/mercado_leitura.py` — a secao nova da guarda de cruzamento (bloco de refutacao +
  `LIMITE_DERIVADO_POR_UNIDADE`, `limite_derivado_do_cruzamento`, `residuo_do_cruzamento`,
  `cruzamento_confere`), `MOTIVO_DO_CRUZAMENTO`, o campo novo em `LinhaLida`, a terceira leitura e
  a chamada da guarda em `ler_linha`, e `_observar_o_cruzamento`
- `l2scanner/mercado_pagina.py` — o **unico chamador de producao** de `ler_linha`: fatia a quarta
  coluna, carrega `mercado_tolerancia_do_cruzamento` e a passa adiante, e passa a exigir
  `mercado_coluna_do_unitario` na conferencia de feature OFF
- `tools/medir_leitura_de_glifo.py` — passa a IMPORTAR a aritmetica do cruzamento de producao, em
  vez de manter a propria copia
- `tests/test_mercado_leitura.py` — +27 funcoes de teste (107 casos coletados no arquivo)
- `tests/test_mercado_pagina.py` — a quarta coluna entra na conferencia de feature OFF

## Decisions Made

Ver `key-decisions` no frontmatter. As duas que merecem destaque em prosa:

**A guarda entra ANTES do OCR, e isso esta preso por teste.** O plano so exigia "depois das tres
celulas e depois da gramatica". A ordem escolhida foi imediatamente depois delas e **antes** do
nome, pela mesma razao ja escrita no passo 3 do pipeline: uma linha que a guarda derruba nunca vai
virar dado, entao pagar ~7 ms de OCR por ela seria pagar por nada.
`test_o_descarte_do_cruzamento_NAO_paga_OCR` afirma ZERO chamadas das duas escalas.

**O cliente parece TRUNCAR o unitario, e nao arredondar — medido nas fixturas.** Em
`janela_negociacao_f005.png`, linha 5, a tela mostra `11,39` por 6 unidades com unitario `1,89`;
mas `1139 / 6 = 1,8983`, que ARREDONDA para `1,90`. Se o cliente trunca, o limite derivado dobra
(um centesimo por unidade em vez de meio) e o residuo de 5 daquela linha cabe. Uma observacao sobre
uma fixtura nao vira lei, mas ela e mais uma explicacao para o fechamento de 0,6525 que reprovou a
guarda, e esta escrita na docstring de `limite_derivado_do_cruzamento` para que quem remedir comece
por ali.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `l2scanner/mercado_pagina.py` teve de mudar, e nao estava em `files_modified`**

- **Found during:** Task 1 (GREEN)
- **Issue:** O `files_modified` do plano (`02-06-PLAN.md:8-9`) lista apenas
  `l2scanner/mercado_leitura.py` e `tests/test_mercado_leitura.py`. Mas `ler_linha` **recebe** os
  recortes de coluna; quem os fatia da janela e `LeitorDePagina._recortes_de_coluna`, em
  `mercado_pagina.py:352`. Um grep amplo confirmou que `mercado_pagina.py:314` e o **unico**
  chamador de producao de `ler_linha`. Sem toca-lo, a coluna do unitario nunca seria recortada
  (a terceira leitura nao aconteceria) e, com a assinatura nova, o tick levantaria `TypeError` —
  verde nos testes do arquivo do plano, quebrado no laco de verdade.
- **Fix:** `_recortes_de_coluna` passou a fatiar `mercado_coluna_do_unitario`; o `__init__` carrega
  `mercado_tolerancia_do_cruzamento`; a chamada de `ler_linha` passa os dois adiante.
- **Files modified:** `l2scanner/mercado_pagina.py`
- **Verification:** `tests/test_mercado_pagina.py -q` verde (29 casos); a contagem da terceira
  leitura roda pelo `LeitorDePagina` inteiro, e nao por `ler_linha` isolada
- **Committed in:** `af4635b`

**2. [Rule 2 - Missing Critical] `mercado_coluna_do_unitario` entrou na conferencia de feature OFF**

- **Found during:** Task 1 (GREEN)
- **Issue:** Sem a chave, `_recortes_de_coluna` faria `int(None["dx"])` e levantaria `TypeError`
  **dentro do tick**, fora de qualquer `try` — derrubando o scanner que existe para avisar que
  alguem da party morreu, por causa de uma coluna de mercado nao calibrada. O plano nao previu a
  conferencia.
- **Fix:** a chave entrou na lista de `_calibrado()`, que ja e o padrao "ausencia e feature OFF com
  aviso alto, nunca `raise` no arranque". `mercado_tolerancia_do_cruzamento` **nao** entrou, de
  proposito: uma guarda que nao se provou nao pode impedir a leitura de acontecer.
- **Files modified:** `l2scanner/mercado_pagina.py`, `tests/test_mercado_pagina.py`
- **Verification:** `TestFeatureOFFQuandoFaltaCalibracao::test_a_leitura_nao_acontece_e_nada_levanta[mercado_coluna_do_unitario]`
- **Committed in:** `d20373d` (o teste) e `af4635b` (o codigo)

**3. [Rule 3 - Blocking] O teste do 02-04 que PROIBIA a terceira leitura foi invertido**

- **Found during:** Task 1 (RED)
- **Issue:** `TestOUnitarioNaoEntraNestePlano::test_a_coluna_do_unitario_NAO_e_recortada_nesta_onda`
  afirmava `"mercado_coluna_do_unitario" not in inspect.getsource(mercado_pagina)`. Ele estava
  certo no 02-04 (ler uma coluna sem consumidor seria leitura morta) e esta errado agora — esta e a
  onda em que o consumidor chega.
- **Fix:** a classe virou `TestOUnitarioELIDOMasNuncaGuardadoComoPreco`, com a afirmacao invertida e
  a razao da inversao escrita na docstring. **O que nao inverteu** e a proibicao de guardar o
  unitario como preco: os dois testes que a prendem continuam identicos.
- **Files modified:** `tests/test_mercado_leitura.py`
- **Verification:** `tests/test_mercado_leitura.py -q` verde
- **Committed in:** `d20373d`

**4. [Rule 3 - Blocking] A aritmetica do cruzamento foi PROMOVIDA em vez de duplicada**

- **Found during:** Task 1 (GREEN)
- **Issue:** `tools/medir_leitura_de_glifo.py` ja tinha `residuo_do_cruzamento` e
  `limite_derivado_do_cruzamento` — foi ele quem as mediu. Escrever as mesmas duas em producao
  criaria **duas versoes da mesma primitiva**, que e exatamente o anti-padrao que a docstring de
  `mercado_leitura` documenta e recusa ("copiar em vez de mover teria produzido duas versoes da
  mesma primitiva"). A duplicacao foi causada diretamente por esta task.
- **Fix:** as duas nasceram em producao (com a semantica `int | None` que o pipeline exige) e a
  ferramenta passou a IMPORTA-LAS, apagando as proprias copias. `LIMITE_POR_UNIDADE` virou apelido
  de `LIMITE_DERIVADO_POR_UNIDADE`. A seta continua apontando ferramenta -> puro, como nos outros
  precedentes desta fase.
- **Files modified:** `l2scanner/mercado_leitura.py`, `tools/medir_leitura_de_glifo.py`
- **Verification:** `tests/test_medir_leitura_de_glifo.py -q` verde, 35 casos, sem uma linha de
  teste alterada
- **Committed in:** `af4635b`

---

**Total deviations:** 4 auto-fixed (3 de Rule 3 - blocking, 1 de Rule 2 - missing critical)
**Impact on plan:** Nenhum aumento de escopo funcional. Tres arquivos fora do `files_modified`
declarado foram tocados (`mercado_pagina.py`, `tools/medir_leitura_de_glifo.py`,
`tests/test_mercado_pagina.py`), todos por consequencia direta da terceira leitura que o plano
manda acrescentar. O `files_modified` do plano estava incompleto: ele nomeia o modulo que muda de
comportamento e esquece o chamador que fatia os pixels.

## Issues Encountered

Nenhum. O GREEN passou na primeira execucao completa, e `ruff check` passou limpo sem retoque.

## Threat Flags

Nenhuma superficie nova. Este plano nao abre porta de rede, nao le arquivo novo, nao instala nada e
nao escreve em disco. As mitigacoes do registro foram aplicadas:

| Ameaca | Estado |
|---|---|
| T-02-32 (`0` lido como `8`) | mitigacao CONSTRUIDA e provada nos testes, mas **DESLIGADA em producao** por reprovacao medida. O risco permanece, com a evidencia (o residuo) agora registrada em toda linha |
| T-02-39 (guarda sem a terceira leitura) | fechada: contagem estrita sobre duas fixturas, 2/2 e 4/4 |
| T-02-36 (guarda nao provada descartando linha boa) | fechada: `None` nunca vira descarte, e sem tolerancia nada e descartado |
| T-02-37 (guarda desligada sem se saber por que) | fechada: veredito literal no fonte, preso por teste de inspecao, e transcrito neste SUMMARY |
| T-02-38 (float na conta do cruzamento) | fechada: aritmetica inteira, sem divisao |
| T-02-SC (instalacoes) | nenhum install |

## Known Stubs

Nenhum. **A guarda desligada nao e stub**: e o resultado medido de um veredito que reprovou,
com o mecanismo inteiro construido, testado nas duas rotas, e o numero de producao gravado como
`None` de proposito. O `02-02-SUMMARY.md` ja tinha registrado a mesma distincao.

## User Setup Required

Nenhum. `mercado_coluna_do_unitario` ja esta calibrada no `calibration.json` da maquina do usuario
desde o 02-01 (portao humano de 2026-08-29) e na `calibracao_de_fixture.json`.

## Verification

| Comando | Resultado |
|---|---|
| `python -m pytest tests/test_mercado_leitura.py -q` | **107 passed** |
| `python -m pytest tests/test_mercado_pagina.py -q` | **29 passed** |
| `python -m pytest tests/test_mercado_27x.py -q` | verde — o detector de morte segue intocado |
| `python -m pytest tests/test_firewall_escopo.py -q` | verde |
| `python -m pytest tests/test_medir_leitura_de_glifo.py -q` | **35 passed**, sem alterar um teste |
| `python -m pytest -q --ignore=tests/test_agenda.py` | **2112 passed, 2 skipped** |
| `python -m pytest tests/test_agenda.py -q` | **132 passed** |
| `ruff check` nos 5 arquivos | `All checks passed!` |

`calibration.json` **NAO foi commitado** e nem tocado: nenhum dos dois commits o contem, e ele
segue gitignored com os 13 moldes do usuario.

## Next Phase Readiness

**Para o 02-07 (wave 6), que vem em seguida e mexe nos MESMOS pontos de chamada:**

- Os tres pontos de leitura de celula em `ler_linha` estao **lado a lado e na mesma forma**
  (`ler_celula_de_numero(recorte, moldes, piso, margem)` para Total e Unitario,
  `ler_celula_de_quantidade(...)` para Quantity), prontos para receber um piso de brilho por coluna
  numa passagem so.
- `LeitorDePagina._recortes_de_coluna` ja fatia as **quatro** colunas no mesmo laco, entao um piso
  por coluna entra ali sem reescrever a fatia.
- **Nenhum piso por coluna foi inventado aqui.** O `1` da coluna Quantity continua com o V=177
  medido pelo 02-04 e a refutacao continua escrita na docstring de `ler_celula_de_quantidade` — o
  numero do 02-07 ainda nao existe, e inventa-lo seria a constante magica que o projeto recusa.
- **Ponto de atencao para o 02-07:** ao mudar o piso da coluna Quantity, a contagem estrita de
  `TestATerceiraLeituraACONTECE` pode passar a incluir linhas que hoje caem por quantidade
  ilegivel. Se alguma delas ler total e quantidade mas nao ler o unitario, a igualdade estrita
  quebra e o relaxamento autorizado pelo plano ("igual ao numero de linhas com total e quantidade
  lidos") passa a ser o criterio certo — **nunca** `> 0` sozinho.

**Para a Fase 3:** `LinhaLida.residuo_do_cruzamento` esta disponivel e documentado como
observacao da Fase 2. **Se ele vai para o CSV e decisao dela**, e nada aqui a antecipa.

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-30*

## Self-Check: PASSED

- `l2scanner/mercado_leitura.py` — FOUND
- `l2scanner/mercado_pagina.py` — FOUND
- `tools/medir_leitura_de_glifo.py` — FOUND
- `tests/test_mercado_leitura.py` — FOUND
- `tests/test_mercado_pagina.py` — FOUND
- commit `d20373d` (test) — FOUND
- commit `af4635b` (feat) — FOUND
- `calibration.json` ausente dos dois commits — CONFERIDO
