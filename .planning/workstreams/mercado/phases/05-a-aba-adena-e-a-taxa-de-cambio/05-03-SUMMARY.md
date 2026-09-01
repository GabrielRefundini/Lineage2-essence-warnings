---
phase: 05-a-aba-adena-e-a-taxa-de-cambio
plan: 03
subsystem: mercado
tags: [adena, taxa-de-cambio, exibicao, csv, tdd, mutacao, divida-tecnica]

requires:
  - phase: 05-a-aba-adena-e-a-taxa-de-cambio
    plan: 01
    provides: "`CHAVE_DA_SERIE_DA_ADENA = 'adena#'`, `NOME_EXIBIDO_DA_ADENA = 'Adena'` e `ler_linha_de_adena` — a sentinela de serie de que a escolha de formatador depende"
  - phase: 03-persistencia-de-observacoes
    provides: "`COLUNAS`, `chave_da_observacao`, `RegistroDeObservacoes`, `observacoes_do_arquivo` — consumidos SEM UMA LINHA de mudanca, e por isso `VERSAO_DO_ESQUEMA` segue em 2"
  - phase: 04-modo-mercado-analise-e-console
    provides: "`formatar_centesimos`, `formatar_unitario_derivado`, `secao_do_vale_quanto`, `TravaDoDestaque` — a irma nova herda a razao da marca `(derivado)` inteira"
provides:
  - "`mercado_console.UNIDADE_DA_TAXA = 1_000_000` — a unica coisa que a exibicao sabe sobre a aba Adena"
  - "`mercado_console.formatar_taxa_derivada(Fraction) -> str` — IRMA de `formatar_unitario_derivado`, nao um parametro com default"
  - "`mercado_console.formatador_do_unitario(chave) -> callable` — UM ponto de decisao para os quatro pontos de chamada"
  - "`mercado_console.descrever_a_quantidade(chave, quantidade) -> str` — `6 unidades` / `10.000.000 de adena`, pelo mesmo criterio"
  - "`tests/test_mercado_registro_adena.py` — 19 testes que transformam o ADEN-03 de argumento em MEDICAO, com dois mutantes rodados"
  - "`deferred-items.md` da Fase 5 — quatro itens com os numeros medidos, e uma correcao ao proprio plano"
affects: [05-04 calibracao da aba adena, quem fechar a Fase 5]

actuals:
  # Mesma escala do `estimate` do plano (chars/4 sobre os `files_modified`
  # inteiros, que e como os 62.000 do plano foram projetados):
  # 160.317 chars / 4 = 40.079.
  # Sobre o DIFF realizado apenas (1.188 insercoes, 15 delecoes) seriam ~11.400.
  tokens: 40079
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Funcao IRMA em vez de parametro com default, quando o valor default errado produz um numero PLAUSIVEL e nao um erro"
    - "Escolha de formatacao concentrada em UM despachante por chave, com o par de saidas exercitado no MESMO texto"
    - "Promessa NEGATIVA (`sem coluna nova`) provada por MUTACAO rodada, com dois mutantes cujos conjuntos de vitimas sao diferentes"

key-files:
  created:
    - tests/test_mercado_registro_adena.py
    - .planning/workstreams/mercado/phases/05-a-aba-adena-e-a-taxa-de-cambio/deferred-items.md
  modified:
    - l2scanner/mercado_console.py
    - l2scanner/mercado_modo.py
    - tests/test_mercado_console.py

key-decisions:
  - "A taxa e `11,60 XM por milhao`, RECALCULADA. `05-RESEARCH.md:621` escreve `116,00` e erra por um fator de dez: `Fraction(11600, 10_000_000)` e centesimo POR ADENA, e vezes 1.000.000 da 1.160 CENTESIMOS, que sao `11,60`. Conferido tambem no segundo par da tela do usuario: `15.000.000` por `300,00` -> `20,00`."
  - "`formatar_taxa_derivada` e IRMA e nao um parametro com default, porque o formatador errado NAO erra feio: `round(Fraction(11600, 10_000_000))` vale ZERO, e a linha sairia `0,00 por unidade (derivado)` — plausivel, e ninguem olharia duas vezes. Ha um teste para CADA formatador sobre a MESMA fracao."
  - "A escolha mora em `formatador_do_unitario`, UM ponto para os quatro pontos de chamada. Quatro `if` divergiriam, e o dia em que um divergisse ele imprimiria `0,00`."
  - "`mercado_analise.py` NAO foi aberto. A unidade `XM por milhao` e de EXIBICAO; menor pedido, mediana e tendencia continuam comparando `Fraction(total, quantidade)` exata, sem saber que existe aba."
  - "`mercado_registro.py` NAO foi aberto, e isso e a AFIRMACAO da Task 3: se tivesse sido preciso mudar o registro para o teste passar, o esquema nao comportava a taxa."
  - "A recusa de layout em `mercado_modo` continua exigindo `layout == 'negociacao'` — so o TEXTO mudou. A negociacao segue sendo a grade de TOPO e a Adena mora aninhada."
  - "`requirements.mark-complete` NAO foi executado, agora tambem por DISJUNCAO DE ARQUIVOS: `REQUIREMENTS.md` e `ROADMAP.md` nao estao no `files_modified` deste plano, e o 05-02 roda em paralelo nesta onda."

patterns-established:
  - "Prova de nao-vacuidade por MUTACAO RODADA, com os numeros na docstring: dois mutantes cujos conjuntos de vitimas sao DIFERENTES, para nenhum dos dois casos poder ser removido como redundante"
  - "Comparar o cabecalho-contrato CONTRA a constante `COLUNAS`, e nunca contra uma string escrita a mao — uma copia a mao validaria a si mesma"
  - "Quando a medicao contradiz o plano, o `deferred-items.md` registra a afirmacao MAIS FRACA e medida, e nomeia o que a confunde"

requirements-completed: [ADEN-03, ADEN-04]

coverage:
  - id: D4
    description: "A serie da Adena sai no console como XM por MILHAO de adena, marcada como derivada, com `n` e recencia"
    requirement: "ADEN-04"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestOsDoisFormatadoresSobreAMESMAFracao"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestOParQueDISCRIMINA_NoMESMOTexto::test_o_n_e_a_recencia_continuam_na_linha_da_adena"
        status: pass
    human_judgment: false
  - id: D5
    description: "A serie de negociacao continua saindo por unidade, no MESMO texto em que a Adena sai por milhao"
    requirement: "ADEN-04"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestOParQueDISCRIMINA_NoMESMOTexto (7 testes, os dois sentidos)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestODestaqueAoVivoDaAdena::test_uma_oferta_de_ITEM_continua_saindo_por_unidade"
        status: pass
    human_judgment: false
  - id: D6
    description: "`mercado_analise` nao ganhou uma linha: a taxa continua sendo `Fraction(total, quantidade)`, exata e sem saber de aba nenhuma"
    verification:
      - kind: static
        ref: "git diff --name-only 8e6000d..HEAD — `mercado_analise.py` NAO aparece"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py (42 testes) verde na verificacao"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_registro_adena.py::TestOMESMOArquivoGuardaAsDUAS::test_a_taxa_da_adena_e_o_unitario_do_item_saem_da_MESMA_aritmetica"
        status: pass
    human_judgment: false
  - id: D7
    description: "Uma `LinhaLida` da Adena atravessa `mercado_registro` ate o CSV e volta — cabecalho e seis colunas inalterados, `VERSAO_DO_ESQUEMA` intacta"
    requirement: "ADEN-03"
    verification:
      - kind: integration
        ref: "tests/test_mercado_registro_adena.py (19 testes, tudo em tmp_path)"
        status: pass
      - kind: mutation
        ref: "mutante 1 (setima coluna nas duas series) -> 11 de 19 caem; mutante 2 (coluna extra so na Adena) -> 11 de 19 caem, conjunto DIFERENTE"
        status: pass
    human_judgment: false
  - id: D8
    description: "O defeito `135,00 -> 13588` esta registrado com os numeros, e NAO foi consertado nesta fase"
    verification:
      - kind: static
        ref: ".planning/.../deferred-items.md item 1, com a tabela de Vmax medida nesta arvore"
        status: pass
    human_judgment: true
    rationale: "E registro de divida, nao codigo. O que o torna auditavel e o controle do instrumento: os dez totais que medi reproduzem EXATAMENTE a tabela gravada pelo 05-01."

duration: 21min
completed: 2026-09-01
status: complete
---

# Phase 5 Plan 03: A unidade da aba Adena e o ADEN-03 medido — Summary

**A exibicao aprendeu UMA coisa sobre a aba Adena — que ali a unidade util e o milhao — `mercado_analise` nao aprendeu nada, e a promessa "a taxa chega ao CSV sem coluna nova" deixou de ser argumento e virou medicao, com dois mutantes rodados para provar que os testes que a afirmam nao sao vacuos.**

## A conta de XM por milhao, RECALCULADA (nao a da pesquisa)

O briefing e o plano mandavam recalcular, e a pesquisa esta errada por um fator de dez.

```
10.000.000 de adena por 116,00 XM

  taxa = Fraction(11600, 10_000_000)   <- CENTESIMOS POR ADENA (= 29/25000)
       x 1.000.000                     = 1160  CENTESIMOS por milhao
  formatar_centesimos(1160)            = "11,60"

  -> "11,60 XM por milhao de adena (derivado)"
```

`05-RESEARCH.md:621` escreve `-> x 1.000.000 = 11600 centesimos = 116,00 XM por milhao`. **O erro foi carregar o `11600` INTACTO para depois da multiplicacao**, como se ele ja fosse o resultado dela — quando ele e o operando. O ROADMAP e o `05-CONTEXT.md` trazem o `11,60`, e a conta acima confere com os dois.

**Conferido com um SEGUNDO par medido na tela do usuario**, para uma constante de ajuste nao poder ficar verde com um caso so:

```
15.000.000 de adena por 300,00 XM
  Fraction(30000, 15_000_000) x 1.000.000 = 2000 centesimos -> "20,00 XM por milhao"
```

E o controle negativo que justifica a fase inteira, tambem executado:

```
formatar_unitario_derivado(Fraction(11600, 10_000_000))
  round(29/25000) = 0  ->  "0,00 por unidade (derivado)"
```

O formatador errado **nao erra feio — erra ZERO**, e com toda a confianca do mundo.

## Performance

- **Duration:** 21 min
- **Tasks:** 3 de 3
- **Files:** 5 (2 criados, 3 modificados) — exatamente o `files_modified` do plano
- **Diff:** 1.188 insercoes, 15 delecoes

## Accomplishments

- **O par que discrimina sai no MESMO texto**, e foi impresso para conferir a olho:

  ```
    Adena
      menor pedido visivel: 116,00 por 10.000.000 de adena = 11,60 XM por milhao de adena (derivado) | n=5 | ha 8 h (31/08 10:00)
      mediana: 11,60 XM por milhao de adena (derivado) | n=5 | oferta mais nova ha 7 h (31/08 10:04)

    Dragon Belt
      menor pedido visivel: 1,00 por 1 unidade = 1,00 por unidade (derivado) | n=5 | ha 8 h (31/08 10:00)
      mediana: 1,02 por unidade (derivado) | n=5 | oferta mais nova ha 7 h (31/08 10:04)
  ```

  Um teste que exercitasse so a Adena passaria com a escolha trocada em **qualquer** sentido.

- **A escolha e UM ponto de decisao**, `formatador_do_unitario(chave_da_serie)`, servindo os quatro pontos de chamada (`destaque_ao_vivo`, `_linha_do_menor`, `_linha_da_mediana`, e o laco de `secao_do_vale_quanto`). O menor pedido e a mediana da mesma serie recebem a MESMA chave — dois numeros da mesma serie em unidades diferentes seria pior que os dois errados, porque o usuario compararia um com o outro.

- **A quantidade tambem mudou de palavra**, pelo mesmo criterio: `10.000.000 de adena`, e nunca `10000000 unidades`. `_linha_do_menor` montava essa frase inline; ela saiu para `descrever_a_quantidade` e virou uma verdade so, com o singular de hoje preservado.

- **O ADEN-03 virou medicao.** `tests/test_mercado_registro_adena.py`, 19 testes, tudo em `tmp_path`, nenhum modulo de producao aberto. Uma `LinhaLida` da sentinela vai ao disco e volta com os tres campos tipados; a taxa que volta e `Fraction(29, 25000)` **exata** (comparada como `Fraction`, nunca como `float`); e o texto `11,60 XM por milhao de adena (derivado)` nasce do que o CSV guardou.

- **`mercado_analise.py` e `mercado_registro.py` nao aparecem no diff.** E a forma mais forte de afirmar que o esquema ja comportava a taxa: se fosse preciso muda-los para o teste passar, ele nao comportava.

## Task Commits

1. **Task 1 (tdd): XM por milhao, escolhido pela chave da serie**
   - RED: `479a55b` (test) — 18 falharam, 57 passaram
   - GREEN: `f9ef2e8` (feat)
2. **Task 2: a divida do 13588, registrada com os numeros**
   - `013d9a3` (docs)
3. **Task 3: a taxa chega ao CSV, e isso e MEDIDO**
   - `01bb2cc` (test)

## Verificacao — CADA `<automated>` com o resultado REAL

| Criterio | Comando exato | Resultado real |
|---|---|---|
| Task 1 `<automated>` | `python -m pytest tests/test_mercado_console.py -x -q` | **75 passed** em 0,43 s |
| Task 1 `<done>` | `python -m pytest tests/test_mercado_console.py tests/test_mercado_modo.py tests/test_mercado_analise.py -q` | **186 passed** em 2,51 s |
| Task 2 `<automated>` | o `python -c` dos seis marcadores, verbatim | **`FALTAM: []`, exit 0** |
| Task 3 `<automated>` | `python -m pytest tests/test_mercado_registro_adena.py tests/test_mercado_registro.py -x -q` | **133 passed** em 4,99 s |
| `<verification>` linha 1 | `python -m pytest tests/test_mercado_console.py -q` | **75 passed** |
| `<verification>` linha 2 | `python -m pytest tests/test_mercado_registro_adena.py -q` | **19 passed** |
| `<verification>` linha 3 | `python -m pytest tests/test_mercado_modo.py tests/test_mercado_analise.py tests/test_mercado_registro.py -q` | **225 passed** em 8,10 s |
| Suite inteira | `python -m pytest tests/ --ignore=tests/test_agenda.py -q` | **4118 passed, 24 skipped** em 99,79 s |

**Base do worktree, medida ANTES de tocar em nada:** `4077 passed, 24 skipped`.
**Delta:** **+41 passed, +0 skipped, 0 falhas.**

O `41` fecha exatamente: **22** testes novos em `test_mercado_console.py` + **19** em `test_mercado_registro_adena.py`. Nenhum teste existente foi removido ou desativado.

(A referencia da main citada no briefing e `4099 passed, 2 skipped`. Este worktree pula 22 a mais, pelo mesmo motivo que o 05-01 ja registrou: fixturas gitignored.)

### `<success_criteria>` do plano, um a um

- [x] `formatar_taxa_derivada(Fraction(11600, 10_000_000))` devolve `"11,60 XM por milhao de adena (derivado)"` — `TestOsDoisFormatadoresSobreAMESMAFracao::test_a_taxa_da_adena_sai_em_XM_por_MILHAO`.
- [x] No MESMO texto de `secao_do_vale_quanto`, a Adena sai em XM por milhao e a negociacao por unidade — `TestOParQueDISCRIMINA_NoMESMOTexto`, sete testes, os dois sentidos.
- [x] `mercado_analise.py` e `mercado_registro.py` nao foram modificados — `git diff --name-only 8e6000d..HEAD` lista **exatamente** os cinco arquivos do `files_modified`.
- [x] Uma `LinhaLida` da Adena faz a ida e volta em `tmp_path`, com seis colunas e cabecalho-contrato intactos — `TestAIdaEVoltaDaTaxa` e `TestOCabecalhoContinuaOMESMO`.
- [x] `VERSAO_DO_ESQUEMA` nao mudou, nenhuma coluna nova — `TestAVersaoDoEsquemaNaoSubiu`, tres testes, e `calibracao.py` fora do diff.
- [x] O `deferred-items.md` da fase existe com os quatro itens e os numeros.

## Vacuidade: o que eu procurei, e o que encontrei

O briefing avisava que **oito criterios ja se revelaram vacuos nesta sessao**. Rodei cada `<automated>` **exatamente como escrito** e cacei vacuidade ativamente. Dois achados.

### 1. Um criterio que EU escrevi pegou a MIM mesmo, em minutos

`test_ela_nao_afirma_mais_que_o_v1_le_SOMENTE_negociacao` varre o FONTE de `laco_do_mercado` — comentarios inclusive — procurando a frase que a Fase 5 tornou falsa. Ao implementar, escrevi um comentario explicando a mudanca e **citei a frase antiga entre aspas**. O teste caiu na hora:

```
E   assert 'le SOMENTE a grade de' not in '...'
E     'le SOMENTE a grade de' is contained here:
E       zer "o v1 le SOMENTE a grade de negociacao" passou a ser
```

**Nao e vacuidade — e o oposto:** e a demonstracao de que a varredura de fonte tem dentes, no mesmo molde do `EXPRESSOES_PROIBIDAS` que a Fase 4 ja usa. O comentario foi reescrito sem citar a frase, com a razao registrada nele: uma afirmacao errada num comentario engana o proximo leitor exatamente como engana o usuario.

### 2. A promessa NEGATIVA da Task 3, provada por MUTACAO e nao por leitura

"Sem coluna nova" e onde criterio vacuo se esconde: um arquivo de testes que so grava e le fica verde num esquema de sete colunas tanto quanto num de seis. Entao **rodei dois mutantes de verdade** contra os 19 testes:

| Mutante | O que ele faz | Resultado REAL |
|---|---|---|
| 1 | Uma SETIMA coluna `taxa_em_centesimos_por_milhao`, preenchida nas duas series | **11 de 19 caem** |
| 2 | A mesma coluna extra **so na linha da Adena**, cabecalho intacto em seis (a forma furtiva: o arquivo continua abrindo no Sheets) | **11 de 19 caem** |

**Os conjuntos de vitimas sao DIFERENTES**, e e isso que justifica os dois casos existirem: `test_sao_SEIS_colunas_e_nenhuma_delas_e_da_taxa` so cai no mutante 1 (o cabecalho mudou), e `test_as_DUAS_linhas_tem_o_MESMO_numero_de_campos` so cai no mutante 2 (a assimetria). Cada um sozinho deixaria um dos dois defeitos passar.

Os oito sobreviventes medem outro eixo — `VERSAO_DO_ESQUEMA`, a dedup em memoria, e o cabecalho comparado CONTRA `COLUNAS` (que por construcao acompanha a constante). Nao sao vacuos; so nao apontam para este defeito. **Os numeros ficaram na docstring do modulo**, para nao envelhecerem em silencio.

## O que a MEDICAO desta fase CONTRADIZ do plano

O plano mandava escrever, no item 1 do `deferred-items.md`, que *"a fixtura de negociacao nao tem nenhuma linha destacada (Vmax 215/226/230 uniformes, conferido)"*. **Eu medi, e e falso.** Sobre a coluna `Total`, com o caminho de producao:

```
  janela_adena_f014.png       230 230 230 226 230 [255] 226 230 230 230   <- a L5 e a UNICA a 255
  janela_negociacao_f005.png  226 226 230 230 230  230  230 230 230 230   <- nenhuma destacada
  janela_negociacao_f010.png [255] 220 220 220 [255] 226 230 230 230 230  <- DUAS a 255
```

**Controle do instrumento:** os dez totais que li da fixtura da Adena (`6200, 6499, 6500, 6600, 6700, 13588, 6800, 6850, 7000, 7000`) reproduzem **exatamente** a tabela que o 05-01 gravou. Sem essa coincidencia, os `Vmax` acima seriam numeros de uma medicao que ninguem sabe se apontava para os pixels certos.

**Mas eu tambem nao superafirmo.** O `f010` e um frame CONFUNDIDO: `tests/test_mercado_leitura.py:36-49` ja documenta que uma tooltip cobre a coluna `Total` das linhas 0 a 3 naquele frame, entao o `Vmax = 255` da L0 e indistinguivel entre "linha destacada" e "tooltip clara". A L4 fica fora do trecho documentado e le `10000`, sem verdade de referencia no repositorio. **A afirmacao que ficou no `deferred-items.md` e a mais fraca e medida**, com o que a confunde nomeado e com o material que a fecharia.

## A divida registrada, e nao consertada

`deferred-items.md` da Fase 5, quatro itens, cada um com sintoma, causa lida no fonte, por que nao foi consertado aqui e o preco de consertar depois:

1. **`135,00` lido como `13588`** — o par `0`x`8`, margem **0,0370**, na linha destacada. As quatro peneiras conferidas uma a uma (gramatica passa; `linha_ocluida` diz limpo; o acordo entre frames CONCORDA no erro; `mercado_tolerancia_do_cruzamento: None`). A Fase 5 o pega **so na Adena**; na negociacao ele continua ATIVO.
2. **O ramo que ACEITA um arredondamento (`133,33 / 66,66`, residuo 1 contra limite 1,0) nao tem pixel no repositorio** — e **inferencia aritmetica verificada em teste de unidade, e nao medicao sobre pixels**. As nove linhas boas da fixtura dividem TODAS exato.
3. **A `Auction List` continua nao sendo lida** — sete pisos varridos, `None` nas dez linhas, sem vale.
4. **A aba `busca`** continua fora, e o `--layout busca` grava geometria orfa.

## Deviations from Plan

### 1. [Rule 1 - Bug, no meu proprio comentario] A frase proibida citada num comentario

Descrita por inteiro em **"Vacuidade"** acima. Encontrada pelo `<automated>` da Task 1, corrigida antes do commit do GREEN. Impacto: nenhum no comportamento.

### 2. [Rule 2 - Correcao de afirmacao] O `deferred-items.md` contradiz o plano onde a medicao contradiz

O plano ditava uma afirmacao sobre as fixturas de negociacao que a medicao refuta. Registrei o **medido**, com o confundidor nomeado, em vez de copiar o ditado. Um `deferred-items.md` que afirmasse algo falso sobre pixels seria pior que nenhum: e um arquivo que existe para ser confiavel quando alguem voltar a ele daqui a meses.

### 3. [Bug do SDK ISOLADO] `state.advance-plan` e `state.record-session` escrevem no STATE.md mesmo falhando

O briefing avisava que "os handlers `state.*` corromperam o `progress` do milestone ARQUIVADO na onda 1". **Isolei qual, e como.**

- `state.advance-plan` devolveu `{"error": "Cannot parse Current Plan or Total Plans in Phase from STATE.md"}` — **e mesmo assim gravou** um frontmatter novo. `progress` foi de `total_phases: 4, completed_phases: 4, total_plans: 21, completed_plans: 21, percent: 100` para `total_phases: 1, completed_phases: 0, total_plans: 4, completed_plans: 1`, **com `percent` apagado**.
- `state.record-session` faz a **mesma** corrupcao (provado com uma sonda `TESTE-SONDA`, depois revertida).
- `state.update-progress` e o unico que se recusa corretamente: `"progress percent withheld by buildStateFrontmatter — STATE.md left unchanged"`.

**O que foi feito:** `git checkout -- .planning/workstreams/mercado/STATE.md` depois de cada sonda, e a atualizacao feita **a mao** em `stopped_at`, `last_updated` e `state_head`. O bloco `progress` foi conferido depois da edicao e esta em `4/4, 21/21, percent 100`. Os blocos `Phase`/`Plan`/`Status` e `current_phase` seguem INTOCADOS — sao do orquestrador, e o STATE.md esta em milestone-complete.

### 4. [Omissao deliberada] `requirements.mark-complete` e `roadmap.update-plan-progress` NAO foram executados

- **Motivo novo, e mais forte que o do 05-01: DISJUNCAO DE ARQUIVOS.** `REQUIREMENTS.md` e `ROADMAP.md` **nao estao no `files_modified` deste plano**, e o contrato desta onda 2 e "arquivos disjuntos, em paralelo com o 05-02". Escrever neles quebraria a garantia sob a qual os dois agentes foram despachados.
- **Motivo herdado:** `ADEN-03` tambem e reivindicado pelo 05-01, e `ADEN-01`/`ADEN-02` pelo 05-02 e 05-04, que ainda nao fecharam. Em producao a Adena so alcanca o CSV depois que o portao de layout do 05-02 entrar — marcar `ADEN-03` como completo hoje afirmaria um caminho que ainda nao existe fim a fim.
- **O que foi feito no lugar:** `requirements-completed: [ADEN-03, ADEN-04]` no frontmatter DESTE summary — a contribuicao deste plano, que e verdadeira e verificada. Quem fechar a Fase 5 tem os dois registros (este e o do 05-01) para marcar de uma vez.

---

**Total deviations:** 4 (1 auto-corrigida por Rule 1; 1 correcao de afirmacao por medicao; 1 bug de ferramenta isolado e contornado; 1 omissao deliberada de passo de estado).
**Impact on plan:** nenhum desvio de escopo. O codigo entregue e exatamente o que o `<action>` das tres tasks descreve.

## Restricoes invioláveis, conferidas uma a uma

- **`VERSAO_DO_ESQUEMA` nao subiu** — segue em `2`; `calibracao.py` nao aparece no diff, e `TestAVersaoDoEsquemaNaoSubiu` a prende DEPOIS de a taxa ter atravessado o disco.
- **`mercado_analise.py` nao foi tocado** alem do que o plano permite — ou seja, nao foi tocado.
- **`rastreador.py`, `visao.py`, `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py`** — nenhum no diff (o outro agente trabalha neles nesta arvore).
- **Nada escrito em `.mercado/` nem em `calibration.json`** — nao existe `.mercado/` neste worktree, e `git status --short` esta VAZIO. Todo teste novo usa `tmp_path`.
- **`recordings/`** — nao lido, nenhum glob. As unicas imagens abertas foram tres fixturas VERSIONADAS, nomeadas uma a uma.
- **Nenhuma dependencia nova (FIRE-01)** — `requirements.txt` intocado.
- **Nenhum `--amend`, nenhum `git stash`, nenhum `git clean`.** Quatro commits atomicos, um por task (dois na Task 1, por TDD).
- **Branch conferida ANTES da primeira edicao:** `worktree-agent-ace224eefd8f56125` — nao e `feat/solo-boss-join`.

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder, `TODO` nem `FIXME` no codigo desta onda. (A varredura acusa `TODO TICK` em `mercado_modo.py:577` — e a palavra portuguesa "todo", pre-existente e fora do meu diff.)

As duas funcoes de exibicao novas tem consumidor imediato: `formatador_do_unitario` e chamada nos quatro pontos do console, e a suite as exercita contra o texto real.

## Threat Flags

Nenhuma superficie nova. As tres funcoes novas de `mercado_console` sao PURAS — texto entra, texto sai; nao abrem janela, nao leem teclado, nao escrevem arquivo, nao tem relogio e nao tocam rede. Os tres itens do `<threat_model>` do plano foram mitigados e medidos:

- **T-05-07** (formatador errado): mitigado por UM ponto de decisao + o par de testes que rende as DUAS strings no mesmo texto, com o `0,00` executavel como controle negativo.
- **T-05-08** (numero derivado copiado como lido): a marca `(derivado)` esta colada as duas saidas e presa por teste.
- **T-05-09** (`mercado_analise` ganhando um `if` de aba): o modulo nao foi aberto, e `tests/test_mercado_analise.py` (42 testes) roda na verificacao como guarda.

## Pergunta aberta ao usuario (herdada do 05-01, agora com um segundo pedido)

1. **Uma gravacao curta da aba Adena com uma linha de preco quebrado** — uma oferta cujo `5 mln increment` nao divida o `Total Price` exatamente, como o `133,33 / 66,66`. Fecha o item 2 do `deferred-items.md`.
2. **NOVO — uma captura da aba de NEGOCIACAO, sem tooltip, com uma linha selecionada/destacada e um valor conhecido terminado em `0`** na coluna `Total`. E o que decide se o defeito do `13588` esta ativo na negociacao ou se ele so acontece na Adena. Hoje a evidencia e ambigua por causa da tooltip do `f010`.

**Nada trava por causa das duas.**

## Next Phase Readiness

**Pronto.** O que o 05-04 (e quem fechar a fase) encontra construido:

- A exibicao da taxa esta completa e nao precisa de nada do 05-02 para ser testada — ela consome `chave_da_serie`, que ja existe desde o 05-01.
- O caminho `LinhaLida -> CSV -> ObservacaoLida -> Fraction -> texto` esta medido ponta a ponta em `tmp_path`. Quando o portao de layout do 05-02 entrar, a unica peca que faltava e a que ALIMENTA esse caminho.
- **Nenhum bloqueador.** `REQUIREMENTS.md` e `ROADMAP.md` seguem intocados de proposito, com o registro completo aqui e no 05-01 para quem os fechar.

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- FOUND `l2scanner/mercado_console.py`
- FOUND `l2scanner/mercado_modo.py`
- FOUND `tests/test_mercado_console.py`
- FOUND `tests/test_mercado_registro_adena.py`
- FOUND `.planning/workstreams/mercado/phases/05-a-aba-adena-e-a-taxa-de-cambio/deferred-items.md`
- FOUND `.planning/workstreams/mercado/phases/05-a-aba-adena-e-a-taxa-de-cambio/05-03-SUMMARY.md`

Commits afirmados, conferidos em `git log`:

- FOUND `479a55b`, `f9ef2e8`, `013d9a3`, `01bb2cc`

Simbolos afirmados, conferidos no interpretador:

```
UNIDADE_DA_TAXA 1000000
formatar_taxa_derivada(Fraction(11600,10_000_000))  '11,60 XM por milhao de adena (derivado)'
formatar_unitario_derivado(Fraction(11600,10_000_000))  '0,00 por unidade (derivado)'
formatador_do_unitario('adena#') is formatar_taxa_derivada  True
formatador_do_unitario('dragon-belt') is formatar_unitario_derivado  True
descrever_a_quantidade('adena#', 10_000_000)  '10.000.000 de adena'
descrever_a_quantidade('dragon-belt', 1)  '1 unidade'
VERSAO_DO_ESQUEMA 2
```

---
*Phase: 05-a-aba-adena-e-a-taxa-de-cambio*
*Plan: 03*
*Completed: 2026-09-01*
