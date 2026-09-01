---
phase: 05-a-aba-adena-e-a-taxa-de-cambio
plan: 01
subsystem: mercado
tags: [adena, taxa-de-cambio, leitura-de-glifo, cruzamento, sentinela-de-serie, tdd]

requires:
  - phase: 02-leitura-de-linha
    provides: "`ler_celula_de_numero`, `limite_derivado_do_cruzamento`, `residuo_do_cruzamento`, `linha_vazia`, `linha_ocluida`, `LinhaLida`, `Descarte`, `_recusar`"
  - phase: 03-persistencia-de-observacoes
    provides: "`COLUNAS` e `chave_da_observacao` do CSV — consumidos SEM mudanca, e por isso `VERSAO_DO_ESQUEMA` segue em 2"
provides:
  - "`mercado_leitura.ADENA_POR_INCREMENTO = 5_000_000` — como o jogo escreve a coluna `5 mln increment`, no fonte pelo precedente de `SUFIXO_DA_GRADE`"
  - "`mercado_leitura.quantidade_de_adena(total, incremento) -> (quantidade, incrementos) | None` — a quantidade DERIVADA das duas colunas de moeda, com `limite_derivado_do_cruzamento` como criterio de aceite"
  - "`mercado_catalogo.CHAVE_DA_SERIE_DA_ADENA = 'adena#'` e `NOME_EXIBIDO_DA_ADENA = 'Adena'` — a sentinela que faz a Adena ser UMA serie so"
  - "`mercado_leitura.ler_linha_de_adena(...)` — a linha da Adena de pixels a `LinhaLida`, sem OCR e sem tocar a coluna `Auction List`"
  - "`tests/test_mercado_adena.py` — 64 testes, com o par que discrimina em sentidos opostos e os controles negativos medidos"
affects: [05-02 portao de layout, 05-03 registro e console da taxa, 05-04 calibracao da aba adena]

actuals:
  # Mesma escala do `estimate` do plano (chars/4 sobre `files_modified` inteiros,
  # que e como os 55.000 do plano foram projetados): 177.967 chars / 4 = 44.492.
  # Sobre o DIFF realizado apenas (988 linhas acrescentadas, 43.452 chars) seriam
  # 10.863 — registrado aqui para o numero nao ficar ambiguo na proxima calibracao.
  tokens: 44492
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Quantidade DERIVADA de duas colunas que leem, quando a coluna que a escreve nao se le"
    - "Sentinela de serie para uma aba cuja identidade nao vem de nome lido"
    - "Guarda aritmetica com criterio REUSADO (nunca recopiado), provado por monkeypatch com controle negativo nos dois sentidos"

key-files:
  created:
    - tests/test_mercado_adena.py
  modified:
    - l2scanner/mercado_leitura.py
    - l2scanner/mercado_catalogo.py

key-decisions:
  - "A quantidade da Adena e DERIVADA (`5.000.000 x round(total / incremento)`), nao lida: a coluna `Auction List` nao se le com os moldes deste projeto em piso de brilho nenhum — varrido 180/200/210/220/230/240/250, `None` nas dez linhas."
  - "O criterio de aceite e `limite_derivado_do_cruzamento`, que JA EXISTIA — reuso, nao mecanismo novo. Provado por monkeypatch: com o limite em 0,0 o caso bom reprova; com o limite em 1000,0 o caso ruim passa."
  - "A comparacao e `residuo <= limite`, e o sinal e LOAD-BEARING: com `<` o caso legitimo `133,33 / 66,66` (residuo 1 contra limite 1,0) REPROVARIA."
  - "A Adena e UMA serie so, com chave-sentinela `adena#` montada do `SEPARADOR_DA_ASSINATURA`. Decisao do usuario; a chave derivada do nome partiria 5M/10M/15M em tres series pela trava de digitos (D-03)."
  - "O cruzamento e GUARDA na Adena e continua OBSERVACAO na negociacao — a unica rede entre uma leitura errada e uma taxa plausivel no CSV."
  - "O incremento ilegivel DERRUBA a linha da Adena, ao contrario do unitario ilegivel na negociacao, que so cala a guarda: sem `Quantity` nao ha outra rota ate a quantidade."
  - "`5_000_000` mora no FONTE, pelo precedente literal de `SUFIXO_DA_GRADE`: nao e numero medido, e como o jogo escreve a coluna, e grava-lo na calibracao criaria duas verdades sobre uma coluna so."

patterns-established:
  - "Tabela de leitura medida versionada COM o teste que a reafirma contra os pixels (`TestAFixturaDaAdenaLeOQueODocstringDiz`), para a tabela nao envelhecer em silencio"
  - "Prova de CHAMADA por monkeypatch, sempre com o controle negativo no sentido oposto — um teste que so afirma o resultado nao distingue criterio reusado de constante inline"
  - "Teste de ASSINATURA (`inspect.signature`) para afirmar a ausencia de uma capacidade: mais forte que contar zero chamadas numa execucao"

requirements-completed: [ADEN-02, ADEN-03]

coverage:
  - id: D1
    description: "A quantidade de adena de uma oferta e derivada das colunas `Total Price` e `5 mln increment`, e a derivacao e recusada quando a aritmetica nao fecha"
    requirement: "ADEN-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestOsDoisCasosDificeis"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestOCriterioEChamadoENaoCopiado"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestOSinalDaComparacao"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uma linha da aba Adena vira `LinhaLida` com identidade de sentinela e quantidade em adena, sem OCR e sem tocar a coluna `Auction List`"
    requirement: "ADEN-03"
    verification:
      - kind: integration
        ref: "tests/test_mercado_adena.py::TestALinhaBoaDaAdena (pixels reais de janela_adena_f014.png)"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_adena.py::TestOCruzamentoEGUARDANaAdena"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestUmaSerieSO"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestNadaAquiLeNome"
        status: pass
    human_judgment: false
  - id: D3
    description: "O ramo que ACEITA um arredondamento (residuo > 0) — exercitado com inteiros literais, mas sem um pixel no repositorio que o contenha"
    requirement: "ADEN-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_adena.py::TestOsDoisCasosDificeis::test_aceita_o_arredondamento_de_133_33_por_66_66"
        status: pass
    human_judgment: true
    rationale: "As nove linhas boas de `janela_adena_f014.png` dividem TODAS exato (residuo 0). O ramo que aceita residuo > 0 e inferencia aritmetica sobre numeros que o usuario VIU na tela, nao medicao sobre pixels versionados. Fechar isso exige material novo — ver `## Pergunta aberta ao usuario`."

duration: 17min
completed: 2026-09-01
status: complete
---

# Phase 5 Plan 01: A quantidade que se deriva e a sentinela da Adena — Summary

**A aba Adena ganhou as duas pecas PURAS de que a taxa de cambio depende: uma quantidade derivada das duas colunas de moeda que leem exatamente (porque a coluna que a escreve nao se le em piso de brilho nenhum) e uma chave de serie sentinela — e, de quebra, a guarda aritmetica que derruba o `13588` que hoje entraria no CSV como taxa `135,88`.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-09-01T15:03:00Z (aprox.)
- **Completed:** 2026-09-01T15:20:06Z
- **Tasks:** 2 de 2
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments

- **`quantidade_de_adena` existe e discrimina os dois casos dificeis conhecidos**, com o criterio REUSADO e nao recopiado: aceita `(13333, 6666) -> (10.000.000, 2)` por IGUALDADE (residuo 1 contra limite 1,0) e rejeita `(13588, 6750)` (residuo 88).
- **O defeito ativo da fixtura foi fechado.** A linha 5 de `janela_adena_f014.png` — em que a tela diz `135,00` e a leitura devolve `13588` — agora vira `Descarte` de motivo `cruzamento`. Confirmado nesta arvore que nem a gramatica nem a sonda de oclusao a pegariam: `linha_vazia` False, `linha_ocluida` False, `135,88` e numero valido.
- **`ler_linha_de_adena` atravessa as nove linhas boas da fixtura** com pixels reais, produzindo `LinhaLida(chave='adena#', nome='Adena', quantidade=5.000.000)` e derrubando a decima.
- **A sentinela nao tem por onde receber OCR**, e isso e afirmado por `inspect.signature` — mais forte que contar zero chamadas numa execucao — com o controle negativo de que `ler_linha` TEM as duas leitoras.
- **Zero mudanca no CSV.** `VERSAO_DO_ESQUEMA` segue em 2, `calibracao.py` nao foi tocado, nenhuma coluna nova.

## Task Commits

1. **Task 1 (tracer, tdd): a quantidade que se deriva, e o criterio que ja existe**
   - RED: `9ab3d8f` (test)
   - GREEN: `1f08bb3` (feat)
2. **Task 2 (tdd): a linha da Adena, sem nome e sem OCR, com identidade de sentinela**
   - RED: `54caedd` (test)
   - GREEN: `677499a` (feat)

## Files Created/Modified

- `tests/test_mercado_adena.py` — **criado.** 64 testes. Carrega, na docstring do modulo, a tabela de leitura medida nesta arvore com o codigo de producao sobre `janela_adena_f014.png`, e `TestAFixturaDaAdenaLeOQueODocstringDiz` a reafirma contra os pixels a cada rodada.
- `l2scanner/mercado_leitura.py` — `ADENA_POR_INCREMENTO`, `quantidade_de_adena` (ao lado de `residuo_do_cruzamento`) e `ler_linha_de_adena` (logo depois de `ler_linha`). Nada existente foi alterado — so acrescimo, mais duas linhas de import.
- `l2scanner/mercado_catalogo.py` — `CHAVE_DA_SERIE_DA_ADENA` e `NOME_EXIBIDO_DA_ADENA`, ao lado de `SEPARADOR_DA_ASSINATURA`, com o argumento do usuario escrito ao lado.

## Verificacao — cada `<automated>` com o resultado REAL

| Criterio | Comando exato | Resultado real |
|---|---|---|
| Task 1 `<automated>` | `python -m pytest tests/test_mercado_adena.py -x -q` | **24 passed** em 0,17 s |
| Task 2 `<automated>` | `python -m pytest tests/test_mercado_adena.py -x -q` | **64 passed** em 2,03 s |
| `<verification>` linha 1 | `python -m pytest tests/test_mercado_adena.py -q` | **64 passed** |
| `<verification>` linha 2 (guarda de regressao) | `python -m pytest tests/test_mercado_leitura.py tests/test_mercado_catalogo.py -q` | **273 passed** em 11,18 s |
| Suite inteira | `python -m pytest tests/ --ignore=tests/test_agenda.py -q` | **4077 passed, 24 skipped** |

**Base do worktree, medida ANTES de tocar em nada:** `4013 passed, 24 skipped`.
**Delta:** **+64 passed, +0 skipped, 0 falhas.** Os 64 sao exatamente os testes novos.
(A referencia da main citada no briefing e `4035 passed, 2 skipped`; este worktree pula 22 a mais, consistente com os ~21 que pulam por fixtura gitignored.)

### `<success_criteria>` do plano, um a um

- [x] `quantidade_de_adena(13333, 6666)` devolve `(10_000_000, 2)` e `quantidade_de_adena(13588, 6750)` devolve `None`, os dois afirmados por teste — `TestOsDoisCasosDificeis`.
- [x] Com `limite_derivado_do_cruzamento` monkeypatchada para `0.0`, `(13333, 6666)` devolve `None` — `TestOCriterioEChamadoENaoCopiado::test_com_o_limite_zerado_o_caso_BOM_reprova`. **A propriedade foi mantida**: a funcao chama o global do modulo, entao um `1.0` copiado inline faria o teste falhar.
- [x] `ler_linha_de_adena` produz `LinhaLida` com a sentinela e, em duas linhas seguidas, UMA serie — `TestUmaSerieSO`.
- [x] `tests/test_mercado_leitura.py` e `tests/test_mercado_catalogo.py` continuam verdes — 273 passed.
- [x] Nada foi escrito em `.mercado/` nem em `calibration.json` — `git status --short .mercado calibration.json` vazio; `git diff --name-only 3c88d0e..HEAD` lista **exatamente** os tres arquivos do plano.

### Restricoes invioláveis, conferidas

- `VERSAO_DO_ESQUEMA` segue em `2` — `calibracao.py` nao aparece no diff.
- `rastreador.py`, `visao.py`, `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py` — nenhum tocado.
- `recordings/` — nao lido, nenhum glob.
- Nenhuma dependencia nova (FIRE-01): `requirements.txt` intocado, e `tests/test_mercado_firewall_de_fase.py::TestNenhumaDependenciaNova` segue verde na suite cheia.
- Nenhum `--amend`, nenhum `git stash`.

## Criterios que se revelaram vacuos, e o que foi feito

**UM, e ele era MEU, nao do plano.** Reportado aqui inteiro porque a instrucao era nunca trocar um criterio calado.

**`test_NUNCA_levanta_e_a_excecao_vira_Descarte` (escrito por mim no RED da Task 2, commit `54caedd`).**

- **O que ele fazia:** passava a string `"isto nao e uma imagem"` como recorte da linha e esperava `Descarte`.
- **O resultado REAL ao rodar:** `assert False, where False = isinstance(None, Descarte)` — ele **falhou**, e a falha expos a vacuidade. `linha_vazia` faz `getattr(bgr, "size", 0) == 0`, e uma `str` nao tem `.size`: a string era classificada como **LINHA VAZIA** e a funcao devolvia `None` sem NUNCA chegar ao `except`. O teste media a PRIMEIRA peneira e afirmava a ULTIMA.
- **O que foi feito:** substituido por `TestNUNCALevanta`, com **tres** testes e o controle negativo medido:
  1. `monkeypatch` sobre `mercado_leitura.linha_ocluida` para levantar `RuntimeError` no MEIO do pipeline, sobre pixels que atravessam de verdade -> `Descarte`.
  2. **Controle negativo:** a MESMA linha, sem a excecao, vira `LinhaLida`. Sem ele, "devolveu Descarte" nao distinguiria o `except` de qualquer outra peneira.
  3. A linha vazia de VERDADE (um `np.ndarray` real, `linha_vazia_par.png`) devolve `None` — a peneira que a versao vacua estava medindo sem saber.
- A razao ficou **escrita na docstring da classe**, para nao voltar.
- **Commitado em:** `677499a`, com a razao na mensagem de commit.

Os demais criterios do plano (`<automated>`, `<done>`, `<success_criteria>`) foram rodados **exatamente como escritos** e nenhum se revelou vacuo.

## Decisoes travadas — nenhuma reaberta

As quatro decisoes marcadas como "nao reabra" no briefing foram implementadas como escritas: a serie unica com chave `adena#` / nome `Adena`; a quantidade DERIVADA e nao lida; o cruzamento como GUARDA na Adena e observacao na negociacao; `5_000_000` no fonte pelo precedente de `SUFIXO_DA_GRADE`. Os argumentos de cada uma estao no fonte, ao lado do codigo, e nao so aqui.

## Deviations from Plan

### 1. [Rule 1 - Bug, em teste proprio] O teste de excecao da Task 2 era vacuo

Descrito por inteiro em **"Criterios que se revelaram vacuos"** acima. Encontrado ao rodar o GREEN da Task 2; corrigido com controle negativo medido; commitado em `677499a`.

### 2. [Rule 4 evitada por conservadorismo] `requirements.mark-complete` NAO foi executado

- **O que o contrato do executor manda:** marcar `ADEN-02` e `ADEN-03` como completos em `REQUIREMENTS.md`, copiando o campo `requirements` do frontmatter deste plano.
- **Por que nao foi feito:** os MESMOS dois IDs sao reivindicados por outros planos desta fase, que ainda nao rodaram — `05-02` reivindica `ADEN-01, ADEN-02`; `05-03` reivindica `ADEN-03, ADEN-04`; `05-04` reivindica `ADEN-01, ADEN-02`. Marcar `ADEN-03` como completo agora afirmaria que "cada linha da Adena vira observacao de TAXA no CSV", que e literalmente o trabalho do `05-03` e nao aconteceu. Seria uma afirmacao falsa num documento que o usuario le.
- **O que foi feito no lugar:** `requirements-completed: [ADEN-02, ADEN-03]` fica no frontmatter DESTE summary (a contribuicao deste plano, que e verdadeira), e `REQUIREMENTS.md` segue com os quatro `Pending`. Quem fechar a fase (o `05-03`/`05-04`, ou o orquestrador ao juntar as ondas) tem o registro completo para marcar de uma vez.
- **Impacto:** nenhum no codigo. `REQUIREMENTS.md` nao aparece no diff.

---

**Total deviations:** 2 (1 auto-corrigida por Rule 1; 1 omissao deliberada de passo de estado, documentada).
**Impact on plan:** nenhum desvio de escopo. O codigo entregue e exatamente o que o `<action>` das duas tasks descreve.

## Issues Encountered

Nenhum bloqueio. A medicao previa contra `janela_adena_f014.png` reproduziu **exatamente** os dez pares da pesquisa (`6200/6200 ... 13588/6750 ... 7000/7000`, `Quantity` em `None` nas dez), entao nenhuma suposicao da pesquisa precisou ser revista.

## Pergunta aberta ao usuario (o `<human-check>` D-F da Task 1)

**O ramo que ACEITA um arredondamento nao tem um pixel no repositorio.** As nove linhas boas de `janela_adena_f014.png` dividem TODAS exato (residuo 0). O caso `133,33 / 66,66` — o unico que exercita o `<=` na borda — vem dos numeros que o usuario VIU na tela em 2026-09-01, e esta exercitado em teste de unidade com inteiros literais, o que e nao-vacuo para a funcao, mas e **inferencia aritmetica e nao medicao sobre pixels**.

**O pedido:** uma gravacao curta da aba Adena com a coluna `5 mln increment` ordenada, contendo pelo menos uma linha cujo incremento **nao divida o total exatamente** (uma oferta de preco quebrado, como o `133,33 / 66,66`).

**Se ele nao conseguir:** o ramo fica declarado como inferencia aritmetica nao medida sobre pixels — o que o plano ja preve que seja registrado no `deferred-items.md` da fase, pelo `05-03`. Nada trava por causa disso.

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder, `TODO` nem `FIXME` no codigo desta onda. As duas funcoes novas tem consumidor imediato nas ondas seguintes (`05-02` chama `ler_linha_de_adena` a partir do portao de layout; `05-03` consome a serie sentinela no registro e no console) — e ate la elas nao sao leitura morta, porque a suite as exercita contra pixels reais.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja registrava. As duas funcoes novas sao PURAS: nao abrem janela, nao leem teclado, nao escrevem arquivo, nao tem relogio e nao tocam rede. `T-05-01` (substituicao de glifo virando taxa plausivel) foi **mitigado e medido** — residuo 88 contra limite 1,0. `T-05-03` (excecao dentro do tick) foi mitigado com o `except Exception` no modelo de `ler_linha`, e a mitigacao esta provada por teste com controle negativo.

## Next Phase Readiness

**Pronto para a onda 2.** O que as ondas seguintes encontram ja construido:

- `05-02` (portao de layout): `ler_linha_de_adena` esta pronta e a assinatura e estavel. Ela espera os recortes ja fatiados — os retangulos de **negociacao** servem, medido: mesmo `dx`, mesmo `dy`, mesma altura, mesma largura, e as colunas `Total` e `Unitario` caem exatamente sobre `Total Price` e `5 mln increment`.
- `05-03` (registro e console): `CHAVE_DA_SERIE_DA_ADENA` esta em `mercado_catalogo`, que `mercado_registro` ja importa em nivel de modulo — o console alcanca a constante sem nenhuma aresta de import nova.
- **Nenhum bloqueador.** A unica pendencia e a pergunta aberta acima, e ela nao trava codigo.

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- FOUND `tests/test_mercado_adena.py`
- FOUND `l2scanner/mercado_leitura.py`
- FOUND `l2scanner/mercado_catalogo.py`
- FOUND `.planning/workstreams/mercado/phases/05-a-aba-adena-e-a-taxa-de-cambio/05-01-SUMMARY.md`

Commits afirmados, conferidos em `git log`:

- FOUND `9ab3d8f`, `1f08bb3`, `54caedd`, `677499a`

Simbolos afirmados, conferidos no interpretador:

```
ADENA_POR_INCREMENTO 5000000
quantidade_de_adena(13333,6666) (10000000, 2)
quantidade_de_adena(13588,6750) None
CHAVE 'adena#' NOME 'Adena'
ler_linha_de_adena callable True
```

---
*Phase: 05-a-aba-adena-e-a-taxa-de-cambio*
*Plan: 01*
*Completed: 2026-09-01*
