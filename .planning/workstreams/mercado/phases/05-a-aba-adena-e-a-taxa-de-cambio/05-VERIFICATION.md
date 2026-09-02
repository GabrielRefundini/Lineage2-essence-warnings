---
phase: 05-a-aba-adena-e-a-taxa-de-cambio
workstream: mercado
verified: 2026-09-02T01:26:45Z
status: passed
score: 20/20 must-haves verified
behavior_unverified: 0
overrides_applied: 0
requirements:
  ADEN-01: satisfied
  ADEN-02: satisfied
  ADEN-03: satisfied
  ADEN-04: satisfied
warnings:
  - id: W1
    titulo: "A guarda de paridade do ciano recusa DEPOIS dos 13 cortes, e o fonte afirma o contrario"
    severidade: warning
    escopo: pos-fase (sessao de debug `total-da-adena-em-ciano-nao-se-le`)
    recomendacao: "registrar como divida (DEBT-06)"
  - id: W2
    titulo: "`_vencedor_medido` e uma REIMPLEMENTACAO do portao dentro do teste"
    severidade: warning
    escopo: tests/test_mercado_adena_pagina.py:350
    recomendacao: "trocar o corpo por `leitor._casamento_do_layout`"
  - id: W3
    titulo: "`chamadas == 0` sem afirmar, no mesmo teste, que a pagina foi lida"
    severidade: info
    escopo: tests/test_mercado_adena_pagina.py:663
  - id: W4
    titulo: "Texto de plano/roadmap envelhecido: 'linha 5 cai por cruzamento' virou 'tinta'"
    severidade: info
    escopo: 05-02-PLAN.md must_haves
deferred: []
human_verification: []
---

# Fase 5: A aba Adena e a taxa de câmbio — Relatório de Verificação

**Goal (ROADMAP):** o `--mercado` passa a ler a aba Adena e a registrar a TAXA
(quanto custa adena em XM Coin), sem perder a leitura da aba de negociação.

**Verificado:** 2026-09-02T01:26:45Z
**Status:** passed
**Re-verificação:** Não — verificação inicial
**Postura:** goal-backward, adversarial. Nenhuma afirmação de SUMMARY foi aceita
como evidência; tudo abaixo foi lido no código, medido em processo próprio, ou
lido dos artefatos de campo (`calibration.json`, `.mercado/observacoes.csv`).

---

## Goal Achievement

### Observable Truths

| # | Verdade | Status | Evidência |
|---|---------|--------|-----------|
| 1 | **ADEN-01** — o `--mercado` reconhece a aba Adena e a lê, sem perder a negociação | ✓ VERIFIED | `mercado_pagina._casamento_do_layout` (l.892) elege por maior score com limiar POR layout; `observar` chama `_layout_confere` imediatamente antes de `_ler_a_pagina` (l.40/45 do corpo) e grava `_layout_atual` a cada tick. Medido em processo próprio: `modelo_de_layout(cal_SEM_layouts,'negociacao')` devolve as mesmas 4 colunas do caso COM a chave. |
| 2 | **ADEN-02** — o modelo de colunas da Adena é PRÓPRIO | ✓ VERIFIED | Medido: `modelo_de_layout(cal,'adena')['colunas'] == {'total','unitario'}` contra `{'nome','quantidade','total','unitario'}` na negociação. `_recortes_de_coluna` (l.1122) itera `modelo["colunas"]` — não mais `getattr` nas 4 chaves de topo. A quantidade é DERIVADA (`quantidade_de_adena`), não lida. |
| 3 | **ADEN-03** — cada linha vira observação de TAXA no CSV, sem coluna nova nem bump de esquema | ✓ VERIFIED | `git diff 3c88d0e..6beaa0f -- l2scanner/mercado_registro.py` é **vazio**: o registro não foi tocado. `VERSAO_DO_ESQUEMA` segue em 2 (o diff em `calibracao.py` só acrescentou comentários). **Artefato de campo:** `.mercado/observacoes.csv` tem o cabeçalho de 6 colunas intacto e 11 linhas `adena#`. |
| 4 | **ADEN-04** — o console exibe XM por MILHÃO, dizendo derivada, com `n` e recência | ✓ VERIFIED | Executado: `formatar_taxa_derivada(Fraction(11500,10_000_000))` → `11,50 XM por milhao de adena (derivado)`. `formatador_do_unitario` é o ÚNICO ponto de decisão e é chamado em `_linha_do_menor` (l.555) e `_linha_da_mediana` (l.594), ambos com `serie.chave`. |
| 5 | `quantidade_de_adena(13333, 6666)` devolve 10.000.000 e 2 incrementos | ✓ VERIFIED | Executado: `(10000000, 2)`. |
| 6 | `quantidade_de_adena(13588, 6750)` devolve `None` | ✓ VERIFIED | Executado: `None`. Também reproduzi o caso de campo: `quantidade_de_adena(19000, 9000)` → `None`, `limite_derivado_do_cruzamento(2)` = `1.0` — bate com a recusa que o usuário viu (`residuo=1000`). |
| 7 | Uma linha da Adena vira `LinhaLida` com sentinela e `Adena`, **sem OCR nenhum** | ✓ VERIFIED | `ler_linha_de_adena` (l.2035) monta `LinhaLida` com `CHAVE_DA_SERIE_DA_ADENA` / `NOME_EXIBIDO_DA_ADENA`. A ausência é ESTRUTURAL: a assinatura não tem `ler_texto` nem `ler_texto_conferencia`, e o ramo `if e_adena` em `_ler_a_pagina` (l.1053) não os passa. Espiões de OCR ficam em 0 no teste ponta a ponta. |
| 8 | Cruzamento que estoura vira `Descarte` motivo `cruzamento`, nunca `LinhaLida` | ✓ VERIFIED | Alcançado ponta a ponta com pixels reais em `test_a_guarda_CONTINUA_LIGADA_e_derruba_o_par_branco_que_nao_fecha` (`70,00` × `64,99`, resíduo 501 contra limite 0,5) **com controle negativo** provando que o portão de cor não tocou aqueles recortes (saturação 0,0). Ver nota W4. |
| 9 | Nenhuma leitura de nome no caminho da Adena — a `Auction List` não é tocada | ✓ VERIFIED | Três criérios independentes: igualdade (não continência) do conjunto de recortes; `dx` de toda coluna da Adena `>=` fim da coluna do nome; zero chamadas de OCR. |
| 10 | `mercado_layouts` é OPCIONAL — ausência é o estado normal | ✓ VERIFIED | `calibracao.py:586` `mercado_layouts: dict | None = None`, lido por `dados.get` (l.899). Medido: carregar a fixtura sem a chave não levanta e a negociação sai idêntica. |
| 11 | `pecas_de_calibracao_de_mercado_faltando` continua com QUINZE itens | ✓ VERIFIED | Executado sobre calibração sem nenhuma chave `mercado_*`: **n = 15**, e `mercado_layouts` **não** está na lista. |
| 12 | O portão devolve o NOME do vencedor, e empate não é veredito | ✓ VERIFIED | `_casamento_do_layout` devolve `str | None`; `if len(vencedores) != 1: return None`. Teste com molde clonado prova o empate, com controle negativo (sem o clone a MESMA janela é lida). |
| 13 | `janela_adena_f014.png` ponta a ponta → 9 linhas de taxa, linha 5 descartada | ✓ VERIFIED | Fixtura versionada e rastreada pelo git (3,2 MB). Teste roda dos pixels, com acordo entre dois frames. Motivo hoje é `tinta` e não `cruzamento` — ver W4; o invariante ("a linha corrompida não vira taxa") não mudou. |
| 14 | `mercado_analise` não ganhou uma linha | ✓ VERIFIED | `git diff --stat 3c88d0e..6beaa0f -- l2scanner/mercado_analise.py` é **vazio**. |
| 15 | A série de negociação continua saindo por unidade, byte a byte | ✓ VERIFIED | `TestOParQueDISCRIMINA_NoMESMOTexto` põe as DUAS séries no MESMO texto e afirma as duas direções (a Adena não diz "unidades"; a negociação continua dizendo). É um par que discrimina, não duas afirmações paralelas. |
| 16 | O defeito `135,00 → 13588` está registrado com os números e NÃO foi consertado | ✓ VERIFIED | `deferred-items.md` item 1: tabela das dez linhas com `Vmax`, as quatro peneiras conferidas uma a uma, e a declaração explícita de que **na negociação o defeito continua ATIVO**. |
| 17 | Uma rodada `--layout adena` não altera NENHUMA chave de topo | ✓ VERIFIED | `_gravar_o_layout_aninhado` (l.2703) não atribui uma única chave de topo, e `calibrar` faz `return` nela (l.3108) ANTES do bloco que grava âncora/grade/colunas. Teste compara JSON PARSEADO antes/depois com as chaves **enumeradas do próprio arquivo**. **Campo:** `calibration.json` do usuário hoje traz as 27 chaves de topo, 13 moldes acromáticos, 13 cromáticos e 3 âncoras, depois da recalibração da Adena. |
| 18 | A mesma rodada GRAVA `mercado_layouts.adena` com cabeçalho, limiar e as duas colunas | ✓ VERIFIED | Lido do `calibration.json` real: `mercado_layouts.adena = {cabecalho, limiar_do_cabecalho: 0.73, colunas: {total:{dx:92,largura:84}, unitario:{dx:392,largura:43}}}`, sem `grade` (delta vazio, herda). |
| 19 | `--layout negociacao` continua escrevendo as chaves de topo como hoje | ✓ VERIFIED | `TestARodadaDeNegociacaoCONTINUAEscrevendoOTopo` — **a classe que impede a de cima de ser vácua** — afirma que a grade e as 4 colunas MUDARAM e que os valores gravados são os que ESTA rodada desenhou. |
| 20 | `--layout adena` sem grade de negociação RECUSA | ✓ VERIFIED | `_conferir_a_base_do_layout` é chamada em `calibrar` na l.2868, **antes do primeiro arrasto**. Testes: `rc != 0`, mensagem cita a grade de negociação, NENHUM arrasto pedido, arquivo NÃO reescrito, + controle negativo (com a grade no lugar a rodada anda). |

**Score:** 20/20 verdades verificadas (0 presentes-mas-não-exercitadas).

---

### Required Artifacts

| Artefato | Esperado | Status | Detalhes |
|---|---|---|---|
| `l2scanner/mercado_leitura.py` | `quantidade_de_adena`, `ler_linha_de_adena`, portão de tinta | ✓ VERIFIED | 260 linhas no diff da fase; ambas as funções substantivas, com a medição escrita ao lado. |
| `l2scanner/mercado_catalogo.py` | sentinela de série | ✓ VERIFIED | `CHAVE_DA_SERIE_DA_ADENA = "adena" + SEPARADOR_DA_ASSINATURA`, `NOME_EXIBIDO_DA_ADENA = "Adena"`, com a razão (não passa por `agrupar`). |
| `l2scanner/mercado_pagina.py` | portão que ESCOLHE, `modelo_de_layout`, despacho de leitora | ✓ VERIFIED | 459 linhas no diff. `LEITORAS_DE_LINHA_POR_LAYOUT` guarda o **nome** e resolve por `globals()` na hora — deliberado, para o despacho ser alcançável por `monkeypatch` e o critério de CHAMADA continuar valendo. |
| `l2scanner/calibracao.py` | `mercado_layouts` opcional + conferências de forma | ✓ VERIFIED | Campo opcional; `_conferir_os_layouts_de_mercado` recusa `negociacao` aninhada, bloco não-objeto, coluna de largura 0, limiar fora da faixa e booleano. |
| `l2scanner/mercado_console.py` | os dois formatadores irmãos + o seletor | ✓ VERIFIED | 152 linhas no diff. `UNIDADE_DA_TAXA = 1_000_000`. Sem parâmetro com default — duas funções com nomes diferentes, pela razão medida (`round(Fraction(11600,10M))` vale zero). |
| `l2scanner/calibrar_mercado.py` | portão de escrita por layout | ✓ VERIFIED | 341 linhas no diff. `_gravar_o_layout_aninhado` + `_conferir_a_base_do_layout`, ambas CHAMADAS. |
| `tests/fixtures/mercado/calibracao_de_fixture.json` | bloco `adena` | ✓ VERIFIED | `mercado_layouts: ['adena']` presente e versionado. |
| `tests/test_mercado_adena.py` | 05-01 | ✓ VERIFIED | 696 linhas. |
| `tests/test_mercado_adena_pagina.py` | 05-02 | ✓ VERIFIED | 751 linhas. |
| `tests/test_mercado_registro_adena.py` | 05-03 (ADEN-03 medido) | ✓ VERIFIED | 539 linhas: ida-e-volta, cabeçalho, dedup, `Fraction` exata, versão. |
| `tests/test_calibrar_layout_nao_apaga_negociacao.py` | 05-04 | ✓ VERIFIED | 1042 linhas, com controles negativos em todos os casos. |
| `deferred-items.md` | 4 itens + o achado de campo | ✓ VERIFIED | 215 linhas no diff da fase, mais a seção `[CAMPO 2026-09-01 17:29]` acrescentada depois. |

---

### Key Link Verification

| De | Para | Via | Status | Detalhes |
|---|---|---|---|---|
| `quantidade_de_adena` | `limite_derivado_do_cruzamento` | reuso do critério | ✓ WIRED | **Provado por CHAMADA, não por existência**: `TestOCriterioNAOEEscolhidoAqui` faz `monkeypatch` do limite para `0.0` (o caso BOM reprova) e para `1000.0` (o caso RUIM passa) — o veredito vira dos DOIS lados pela mesma alavanca, mais um controle sem patch. |
| `ler_linha_de_adena` | `LinhaLida` da Fase 3 | mesmo dataclass | ✓ WIRED | O CSV real guarda as 11 linhas da Adena nas MESMAS 6 colunas das de item. |
| `_casamento_do_layout` | `_ler_a_pagina` | `self._layout_atual` escolhe modelo **e** leitora | ✓ WIRED | `observar` chama o portão imediatamente antes; `_ler_a_pagina` sai com `LeituraDaPagina` vazia se não houver vencedor. Sem staleness possível — `_layout_atual` é reescrito a cada `_layout_confere`. |
| `mercado_layouts.adena.grade` | `mercado_grade` | herança de campo (D-D) | ✓ WIRED | `modelo_de_layout` faz `propria.get(campo, grade_de_topo.get(campo))`; medido: o bloco real não tem `grade` e a grade sai completa com `layout: 'adena'`. |
| `chave_da_serie` | qual formatador | `formatador_do_unitario` | ✓ WIRED | Um ponto de decisão; os dois consumidores (`menor`, `mediana`) recebem a MESMA chave, vinda de `serie.chave` no laço. |
| `args.layout` | destino da escrita | `if not e_negociacao: return _gravar_o_layout_aninhado(...)` | ✓ WIRED | O `return` está ANTES de qualquer atribuição de chave de topo (l.3108 contra l.3121+). |
| `cal.mercado_templates_de_digito_cromatico` | `ler_linha_de_adena` | `self._moldes_cromaticos` | ✓ WIRED | `mercado_pagina.py:528` carrega, `l.1060` passa ao ramo da Adena. |

---

### Data-Flow Trace (Level 4)

| Artefato | Valor exibido | Fonte | Dado real? | Status |
|---|---|---|---|---|
| console — menor pedido | `11,50 XM por milhao` | `menor_pedido_visivel(observacoes)` → `.mercado/observacoes.csv` | Sim — 11 linhas gravadas em campo | ✓ FLOWING |
| console — mediana | `formatador_do_unitario(serie.chave)(mediana.unitario)` | `mediana_dos_unitarios` sobre o mesmo CSV | Sim | ✓ FLOWING |
| CSV — `quantidade` | `10000000` / `15000000` | `quantidade_de_adena(total, incremento)` derivada de duas leituras de pixel | Sim | ✓ FLOWING |
| CSV — `total_em_centesimos` | `11500`, `13333`, ... | `ler_celula_de_numero` sobre o recorte `total` do modelo da Adena | Sim | ✓ FLOWING |
| CSV — `residuo_do_cruzamento` | `0` (9×), `1` (2×) | `residuo_do_cruzamento(total, incremento, incrementos)` | Sim | ✓ FLOWING |

**Nota de campo relevante:** os dois resíduos `1` (`13333` e `11955`) são o
**ramo de aceitação por arredondamento** que o `deferred-items.md` item 2
declarava exercitado apenas com inteiros literais. Ele agora tem **pixels de
campo por trás**. O item 2 pode ser reduzido — a lacuna que ele descreve foi
parcialmente fechada em produção.

---

### Behavioral Spot-Checks

Todos executados em processo próprio, sem subir o modo e sem escrever em disco.

| Comportamento | Comando | Resultado | Status |
|---|---|---|---|
| A taxa sai em XM por milhão | `formatar_taxa_derivada(Fraction(11500,10_000_000))` | `11,50 XM por milhao de adena (derivado)` | ✓ PASS |
| A conta do ROADMAP fecha (não o `116,00` da pesquisa) | `formatar_taxa_derivada(Fraction(11600,10_000_000))` | `11,60 ...` | ✓ PASS |
| O segundo par do usuário | `formatar_taxa_derivada(Fraction(30000,15_000_000))` | `20,00 ...` | ✓ PASS |
| O formatador ERRADO dá zero (razão de serem dois) | `formatar_unitario_derivado(Fraction(11600,10_000_000))` | `0,00 por unidade (derivado)` | ✓ PASS |
| O seletor escolhe pela sentinela | `formatador_do_unitario('adena#')` / `('dragon-belt#x')` | `formatar_taxa_derivada` / `formatar_unitario_derivado` | ✓ PASS |
| A quantidade é descrita em adena | `descrever_a_quantidade('adena#', 10000000)` | `10.000.000 de adena` | ✓ PASS |
| Caso-bandeira do arredondamento | `quantidade_de_adena(13333,6666)` | `(10000000, 2)` | ✓ PASS |
| A guarda rejeita o `13588` | `quantidade_de_adena(13588,6750)` | `None` | ✓ PASS |
| **A recusa vista em campo hoje** | `quantidade_de_adena(19000,9000)` | `None`, limite `1.0` | ✓ PASS |
| O despacho de leitora | `leitora_de_linha('adena')` / `('negociacao')` | `ler_linha_de_adena` / `ler_linha` | ✓ PASS |
| A lista das quinze | `pecas_de_calibracao_de_mercado_faltando(cal_vazia)` | `15`, sem `mercado_layouts` | ✓ PASS |
| Sem a chave, a negociação é idêntica | `modelo_de_layout(cal_sem_layouts,'negociacao')` | mesmas 4 colunas | ✓ PASS |
| O modelo da Adena tem DUAS colunas | `modelo_de_layout(cal,'adena')['colunas']` | `{'total','unitario'}` | ✓ PASS |
| Feature OFF sem a chave | `modelo_de_layout(cal_sem_layouts,'adena')` | `None` (não levanta) | ✓ PASS |

**Suíte completa (uma única execução):**
`python -m pytest tests/ --ignore=tests/test_agenda.py -q` →
**4382 passed, 2 skipped, 0 failures** em 197 s.
(Verde de referência informado: 4366 + 2. A diferença são testes dos workstreams
`tiat`/`identidade`, que commitam nesta mesma árvore.)

Arquivos da fase, isolados: **332 passed** em 23 s.

---

### Artefatos de campo conferidos (leitura, sem escrita)

| Artefato | O que confere |
|---|---|
| `calibration.json` | `versao: 2`; 27 chaves `mercado_*` de topo presentes; `mercado_grade.layout == 'negociacao'`; `mercado_layouts == ['adena']` com as duas colunas de moeda e limiar 0,73, **sem** bloco de grade (herda); 13 moldes acromáticos **e** 13 cromáticos em chaves separadas; 3 âncoras. **A calibração de negociação sobreviveu à recalibração da Adena.** |
| `.mercado/observacoes.csv` | Cabeçalho de 6 colunas byte a byte; 11 linhas `adena#;Adena;...`; quantidades `10000000`/`15000000`; resíduos `0` (9×) e `1` (2× — `13333` e `11955`, os dois legítimos). Nenhuma taxa falsa. |

---

### Requirements Coverage

| Requisito | Plano de origem | Status | Evidência |
|---|---|---|---|
| ADEN-01 | 05-02, 05-04 | ✓ SATISFIED | Verdades 1, 10, 11, 12, 17, 19, 20 + `calibration.json` de campo |
| ADEN-02 | 05-01, 05-02, 05-04 | ✓ SATISFIED | Verdades 2, 5, 6, 9, 18 |
| ADEN-03 | 05-01, 05-03 | ✓ SATISFIED | Verdades 3, 7, 14 + as 11 linhas no CSV real |
| ADEN-04 | 05-03 | ✓ SATISFIED | Verdades 4, 15 + 6 spot-checks de formatação |

Nenhum requisito órfão: `REQUIREMENTS.md` mapeia exatamente ADEN-01..04 para a
Fase 5, e os quatro aparecem no `requirements:` de pelo menos um plano.

---

### Test Quality Audit

| Arquivo | Req | Ativos | Skipped | Circular | Nível de asserção | Veredito |
|---|---|---|---|---|---|---|
| `test_mercado_adena.py` | ADEN-02, 03 | todos | 0 | não | Comportamental (monkeypatch que vira o veredito nos dois sentidos) | FORTE |
| `test_mercado_adena_pagina.py` | ADEN-01, 02 | todos | 1 condicional (fixtura ausente — a fixtura ESTÁ versionada) | não | Comportamental, dos pixels | FORTE, com W2 |
| `test_mercado_registro_adena.py` | ADEN-03 | todos | 0 | não | Valor (`Fraction` exata) + ida-e-volta em disco | FORTE |
| `test_mercado_console.py` | ADEN-04 | todos | 0 | não | Valor, em par que discrimina as duas séries no MESMO texto | FORTE |
| `test_calibrar_layout_nao_apaga_negociacao.py` | ADEN-01 | todos | 0 | não | Estado antes/depois sobre JSON parseado + par negativo | FORTE |

**Testes desabilitados sobre requisito:** 0.
**Padrões circulares:** 0. A procedência dos valores esperados é externa ao
sistema — pixels de fixturas versionadas e a captura de tela do usuário.
**Asserções insuficientes:** 2 (W2, W3 — nenhuma bloqueante).

**O que merece nota positiva, porque é exatamente o padrão de defeito que esta
sessão perseguia:** `TestNUNCALevanta` **documenta no próprio docstring uma
versão anterior VÁCUA de si mesma** ("o teste media a primeira peneira e
afirmava a ultima") e explica o instrumento correto. E `TestOCriterioNAOEEscolhidoAqui`
é escrito explicitamente como critério de CHAMADA e não de existência: *"Um
teste que so afirmasse o RESULTADO nao distinguiria os dois... So substituindo a
funcao e vendo o veredito MUDAR e que se prova que ela foi CHAMADA."*

---

### Anti-Patterns Found

| Arquivo | Linha | Padrão | Severidade | Impacto |
|---|---|---|---|---|
| — | — | — | — | Nenhum marcador de dívida (`TODO`/`FIXME`/`XXX`/`TBD`/`HACK`) nos arquivos da fase. As 20 ocorrências de `TODO` são a palavra portuguesa "todo/todos/toda" em comentários. |

---

## O que está PROVADO

1. **A Adena é lida de verdade, dos pixels ao CSV.** O caminho inteiro está
   ligado: portão de layout que ESCOLHE → modelo de coluna próprio → leitora
   própria → `LinhaLida` com sentinela → CSV de 6 colunas. Verificado por teste
   ponta a ponta sobre fixtura versionada **e** por 11 linhas gravadas em campo.

2. **A negociação não foi perdida, e isso está preso dos dois lados.** No
   leitor: sem `mercado_layouts` a negociação sai idêntica (medido). Na
   ferramenta: `--layout adena` não atribui uma única chave de topo, e a classe
   `TestARodadaDeNegociacaoCONTINUAEscrevendoOTopo` prova que o mesmo aparelho
   de teste É capaz de detectar mutação — sem ela, "nada mudou" seria vácuo.
   Confirmado em campo: o `calibration.json` do usuário tem as 27 chaves de topo,
   os 13 moldes e as 3 âncoras depois da recalibração.

3. **A guarda de cruzamento funciona, e ela é chamada.** O critério é
   `limite_derivado_do_cruzamento`, e a prova é de CHAMADA (monkeypatch virando
   o veredito nos dois sentidos), não de existência. Reproduzi a recusa exata de
   campo: `total=19000 incremento=9000 → None`, limite `1,0`, resíduo `1000`.

4. **A pesquisa errou por um fator de dez e o código NÃO copiou o erro.**
   `formatar_taxa_derivada(Fraction(11600, 10_000_000))` devolve `11,60`, não
   `116,00`. O erro está nomeado no docstring da função, com a conta por extenso
   e o apontamento para `05-RESEARCH.md:621`.

5. **`149,44` é ciano e vem da NEGOCIAÇÃO — está registrado.**
   `mercado_leitura.py:285` diz, textualmente, que 193 das 313 células de
   negociação que o portão de cor passa a recusar leem CERTO hoje, *"o `149,44`
   documentado entre elas"*. E o censo de 4.248 células separa 4.028 de
   negociação de 220 da Adena, com 401 cromáticas. O conjunto cromático nunca
   foi característica da Adena, e o fonte diz isso.

6. **O `135,00 → 13588` está registrado com números e não foi consertado.**
   `deferred-items.md` item 1 traz a tabela das dez linhas com `Vmax`, as quatro
   peneiras conferidas uma a uma, e a declaração explícita de que na negociação o
   defeito **continua ativo** — além de corrigir uma afirmação FALSA que o
   próprio plano mandava escrever (`f010` tem duas linhas destacadas, não zero).

---

## O que está AFIRMADO mas não provado por mim

1. **"35 páginas lidas contra 6 perdidas"** — testemunho de campo do usuário.
   Não há `scanner.log` na raiz para conferir. **Corroborado indiretamente**
   pelas 11 observações no CSV e pela consistência da linha de console citada
   (`115,00 por 10.000.000 = 11,50`, e `11500` é de fato o menor total de 10M
   entre as 11 linhas — conferi).

2. **A ordem `_layout_confere` antes de `_ler_a_pagina`** tem, além do teste
   funcional em `observar`, um teste que compara `fonte.index(...)` no texto do
   método (`test_mercado_pagina.py:393`). Esse segundo é um critério de TEXTO, e
   sozinho não provaria nada. Ele não é o único — a fiação real está coberta —,
   mas registro que ele existe.

3. **O ramo de aceitação por arredondamento** (`resíduo > 0`) foi declarado no
   `deferred-items.md` como "inferência aritmética, não medição sobre pixels".
   Isso **mudou hoje**: os dois resíduos `1` no CSV vieram de pixels de campo. O
   item 2 do `deferred-items.md` está desatualizado a favor do projeto.

---

## O que ficou ABERTO

### W1 — A guarda de paridade do ciano recusa TARDE, e o fonte afirma o contrário

**Julgamento pedido pelo usuário: SIM, isto deve virar dívida registrada.**

Medido no fonte, não suposto. `_calibrar_so_digitos` executa, nesta ordem:

```
l.2586  cortados  = cortar_glifos(...)        <- OS TREZE ARRASTOS DE MOUSE
l.2587  fundidos  = fundir_glifos(...)
l.2595  _gravar_os_glifos(...)  ->  l.2491  conferir_a_paridade_do_ciano(fundidos)
```

A guarda roda **depois** de todos os cortes. Ela impede a ESCRITA, não a sessão
de farm — e o custo medido em campo foram **duas rodadas completas** do usuário.

O que a torna dívida e não apenas uma limitação é que **duas afirmações no
repositório dizem o contrário**:

- `calibrar_mercado.py:2489-2490`: *"um conjunto ciano cortado na faixa zebrada
  errada tem de custar uma mensagem, e nao uma sessao de farm"* — custa a sessão
  de farm.
- `debug/total-da-adena-em-ciano-nao-se-le.md:468`: *"A GUARDA DE PARIDADE, que
  e o que impede o esforco jogado fora"* — impede o arquivo estragado, não o
  esforço.

Pela regra da casa ("um número que caiu precisa dizer que caiu"; nunca afirmar
mais do que se mediu), as duas frases precisam ser corrigidas ou a guarda
precisa subir. **Recomendação:** abrir `DEBT-06` em `REQUIREMENTS.md`.
O conserto barato existe: conferir a paridade **no primeiro `0` cortado**, dentro
do laço de `cortar_glifos`, e abortar ali — o `anel_do_zero_esta_partido` já é
uma função pura sobre um molde só, e não precisa do conjunto fundido.

*Escopo: este código entrou na sessão de debug pós-fase, não na Fase 5. Não conta
contra o veredito desta fase.*

### W2 — `_vencedor_medido` é uma reimplementação do portão dentro do teste

`tests/test_mercado_adena_pagina.py:350` refaz, no teste, a lógica de
`_casamento_do_layout` (limiar por layout → `max` → empate devolve `None`).
`test_o_vencedor_por_banda` mede, portanto, **a cópia**, não a função de
produção. É a família exata de defeito que esta sessão persegue: o critério
afirma um comportamento que a produção poderia perder sem o teste ficar vermelho.

**Contido, e por isso é aviso e não gap:** `TestOPortaoESCOLHEEmVezDeSoRecusar`
chama `leitor._casamento_do_layout` de verdade, e o teste ponta a ponta passa por
`observar`. **Conserto de uma linha:** trocar o corpo de `_vencedor_medido` por
`leitor._casamento_do_layout(janela, origem)`.

### W3 — `chamadas == 0` sem afirmar, no mesmo teste, que houve leitura

`test_NENHUMA_chamada_de_OCR_na_pagina_da_adena` (l.663) afirma que os dois
espiões de OCR ficaram em zero, mas não afirma na mesma função que a página foi
aceita. Uma página recusada satisfaria o teste.

**Por que fica em INFO:** a ausência é *estrutural* — `ler_linha_de_adena` não
tem os parâmetros `ler_texto`/`ler_texto_conferencia` (preso por
`inspect.signature` com controle negativo sobre `ler_linha`), e o ramo `if e_adena`
em `_ler_a_pagina` não os passa. Ainda assim, acrescentar
`assert len(aceita.linhas) == 9` nessa função custa uma linha e remove a
dependência de um teste irmão.

### W4 — Texto de plano envelhecido: `cruzamento` → `tinta`

O `must_haves` do 05-02 diz *"descarta a linha 5 com motivo `cruzamento`"*. Depois
do conjunto cromático, a linha 5 cai **antes**, por `tinta`. O invariante que
importa não mudou (a linha corrompida não vira taxa), a mudança está documentada
no docstring do teste e no `deferred-items.md`, e o ramo `cruzamento` continua
alcançado ponta a ponta por outro par. **Não é gap** — é wording de plano que
ficou para trás de uma correção posterior.

---

## Gaps Summary

**Nenhum gap.** Os quatro requisitos estão satisfeitos com evidência de código,
de teste e de campo. Os quatro avisos acima são recomendações de melhoria e
higiene de afirmação; nenhum deles impede a fase de ser considerada entregue,
e três dos quatro nem sequer são código da Fase 5.

A qualidade de teste desta fase é acima da média do projeto: cada afirmação forte
vem com o seu controle negativo, os critérios centrais são de CHAMADA e não de
existência, e um teste chega a documentar a própria versão vácua anterior para
que ela não volte. W2 é a única sobra do padrão perseguido, e é de uma linha.

---

*Verificado: 2026-09-02T01:26:45Z*
*Verificador: Claude (gsd-verifier), postura adversarial*
*Escopo: workstream `mercado`. Achados em `respawn.py`, `bosses.py`, `agenda.py`,
`sessao.py`, `identidade.py` ou `discord/` seriam de outro workstream e não foram
considerados.*
