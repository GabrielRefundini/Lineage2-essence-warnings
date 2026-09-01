---
phase: 05-a-aba-adena-e-a-taxa-de-cambio
plan: 04
subsystem: mercado
tags: [adena, calibracao, portao-de-escrita, aditividade, mutacao, gitignored]

requires:
  - phase: 05-a-aba-adena-e-a-taxa-de-cambio
    plan: 02
    provides: "a forma de `mercado_layouts[<nome>]`, `CAMPOS_HERDADOS_DA_GRADE`, `modelo_de_layout` e `_conferir_os_layouts_de_mercado` — consumidos SEM mudanca"
  - phase: 05-a-aba-adena-e-a-taxa-de-cambio
    plan: 01
    provides: "`CHAVE_DA_SERIE_DA_ADENA` e a medicao de que os 13 moldes ja leem a Adena exatamente — o argumento de NAO cortar glifo aqui"
provides:
  - "`calibrar_mercado.COLUNAS_DA_ADENA` e `COLUNAS_A_MARCAR_POR_LAYOUT` — o conjunto de colunas por layout, com `busca` FORA por nao ter modelo medido"
  - "`calibrar_mercado.FAIXA_DE_CABECALHO_POR_LAYOUT` — o rotulo que o usuario LE na tela, por aba"
  - "`calibrar_mercado.grade_que_difere_do_topo(grade, grade_de_topo)` — o DELTA da grade sobre `CAMPOS_HERDADOS_DA_GRADE`, importado do LEITOR"
  - "`calibrar_mercado._conferir_a_base_do_layout` — as tres recusas que acontecem ANTES do primeiro arrasto"
  - "`calibrar_mercado._gravar_o_layout_aninhado` — a escrita que nao atribui UMA chave de topo"
  - "`tests/test_calibrar_layout_nao_apaga_negociacao.py` — 43 casos, com a mutacao do portao MEDIDA"
affects: [quem fechar a Fase 5]

actuals:
  # Mesma escala do `estimate` do plano (chars/4 sobre os `files_modified`
  # inteiros, que e como os 60.000 do plano foram projetados):
  # `calibrar_mercado.py` 143.791 chars + o teste novo 39.708 = 183.499 / 4.
  # Sobre o DIFF realizado apenas (1.375 insercoes, 23 delecoes em 3 arquivos)
  # seriam ~13.700 — registrado aqui para o numero nao ficar ambiguo na proxima
  # calibracao de estimativa.
  tokens: 45874
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Portao de ESCRITA por layout: o argumento decide o DESTINO, e nao so o rotulo gravado"
    - "Delta calculado sobre a lista de campos importada de quem LE, nunca uma segunda copia no escritor"
    - "Recusa antes do primeiro arrasto, e nao depois da sessao de marcacao"
    - "Arnes de teste que DISPONIBILIZA o que a rodada boa nao deve pedir, para o mutante morrer na afirmacao e nao no arnes"
    - "Disciplina de `tmp_path` promovida de convencao por caso a fixture autouse que desvia o padrao do modulo"

key-files:
  created:
    - tests/test_calibrar_layout_nao_apaga_negociacao.py
  modified:
    - l2scanner/calibrar_mercado.py
    - tests/test_calibrar_mercado.py

key-decisions:
  - "`--layout` deixou de ser rotulo e passou a decidir o DESTINO da escrita. `negociacao` grava as chaves de topo byte a byte como antes; qualquer outro layout grava SO `mercado_layouts[<nome>]` e nao atribui UMA chave de topo."
  - "A `grade` do bloco sai como DELTA sobre `CAMPOS_HERDADOS_DA_GRADE`, e a lista vem IMPORTADA de `mercado_pagina` — quem escreve o delta usa a mesma lista de quem herda. Duas listas divergiriam, e a divergencia grava um campo que o leitor nao le."
  - "Medido: o delta da Adena sai VAZIO com a geometria de hoje, e o bloco sai sem `grade` nenhuma. E o resultado certo (D-D), e ha controle negativo provando que uma geometria diferente SAI gravada."
  - "Sem molde de cabecalho, NADA e gravado e a rodada devolve 1 (T-05-11). O molde E o portao: um bloco sem ele e um layout que o leitor nunca escolhe, e o arquivo passaria a AFIRMAR uma calibracao que nao existe."
  - "A rodada de layout aninhado NAO corta glifo. Os 13 moldes ja leem a Adena exatamente (6200/6200, 6499/6499, 6500, 6600, 6700, 6800, 6850, 7000, 7000), e fundir moldes de uma aba com outra iluminacao entraria em `mercado_templates_de_digito`, que e chave de TOPO — os mesmos 13 que custaram o resgate manual de 2026-08-30."
  - "`--layout busca` passou a ser RECUSADA. Ninguem mediu o modelo de coluna dela e ela nao tem leitora (05-02); ate hoje ela marcava as QUATRO da negociacao e gravava o topo, que e a mesma bomba."
  - "O resumo impresso no fim foi reescrito. O laco antigo le `cal.mercado_coluna_do_nome` e mostraria a calibracao ANTIGA como resultado desta rodada — plausivel e falso."
  - "As caixas `Coluna: nome` e `Coluna: quantidade` ficam DISPONIVEIS no arnes de teste da adena de proposito: sem elas o mutante morre no proprio arnes, e um teste cuja rede e o arnes mediu o arnes."

requirements-completed: [ADEN-01, ADEN-02]

duration: 47min
completed: 2026-09-01
status: complete
---

# Phase 5 Plan 04: `--layout adena` deixou de ser uma bomba — Summary

**O calibrador passou a escrever POR LAYOUT: `--layout adena` grava só `mercado_layouts.adena` e não atribui UMA chave de topo, e a prova não é o `git status` (o arquivo é gitignored, a saída é vazia sempre) — é a comparação do JSON PARSEADO antes e depois, com o mutante do portão revertido medido a reprovar exatamente onde deve.**

## O PORTÃO, medido nos cinco casos

Todos os números abaixo saíram de rodadas reais de `calibrar` sobre os dois frames versionados, com `--calibracao` apontando para dentro de `tmp_path`.

| # | O que o caso afirma | Resultado |
|---|---|---|
| 1 | `--layout adena` não muda NENHUMA chave de topo `mercado_*`, nem faz nenhuma desaparecer | **5 casos passam** |
| 2 | E a rodada FEZ alguma coisa: `mercado_layouts.adena` com cabeçalho, limiar e as duas colunas | **7 casos passam** |
| 3 | **O PAR QUE DISCRIMINA** — `--layout negociacao` com retângulos DIFERENTES: `mercado_grade` e as 4 colunas de topo MUDARAM | **7 casos passam** |
| 4 | A recusa sem base, antes de qualquer arrasto | **9 casos passam** |
| 5 | A ida e volta: o arquivo gravado carrega e produz as 9 linhas de taxa | **4 casos passam** |
| — | O que a rodada de adena nem chega a pedir (janelas e perguntas) | **4 casos passam** |
| — | A disciplina do `tmp_path`, afirmada por estrutura | **3 casos passam** |
| — | Guardas de vacuidade (fixturas existem, semente não é escrita) | **4 casos passam** |

**43 casos, 43 verdes.**

### O caso 3 é quem impede o caso 1 de ser vácuo

Um portão que simplesmente parasse de escrever em tudo passaria nos casos 1 e 2. A rodada de negociação marca retângulos deliberadamente diferentes dos semeados — grade `dx -425` contra `-427`, `dy 258` contra `256`, `largura 940` contra `944`, `altura 448` contra `450`, `altura_da_linha 46` contra `45`; cada coluna deslocada de 2 px e encolhida — e as chaves de topo **têm** de mudar. Além de "mudou", cada caso afirma que mudou **para o que ESTA rodada desenhou**, porque "mudou" sozinho não diz que mudou para o certo.

## A MUTAÇÃO MANUAL, feita à mão e MEDIDA

Reverti o portão da Task 1 no fonte (`e_negociacao = True` e `colunas_a_marcar = COLUNAS_A_MARCAR`, que é literalmente o código de antes), rodei os casos 1 e 5, e restaurei com `git checkout -- l2scanner/calibrar_mercado.py`.

**Primeira medição — e ela me fez CONSERTAR o teste.** O mutante morreu no próprio arnês:

```
E   AssertionError: sem sugestao para 'Coluna: nome'
4 failed, 2 passed, 3 errors
```

Isso é uma reprovação, mas é a reprovação errada: o teste não mediu o portão, mediu o arnês. Acrescentei `Coluna: nome` e `Coluna: quantidade` ao dicionário de caixas da adena — **disponíveis, e ainda assim nunca pedidas**, o que passou a ser afirmado à parte por igualdade de lista. Segunda medição:

| Caso | Teste | Com o portão | Com o portão REVERTIDO |
|---|---|---|---|
| 1 | `test_nenhuma_chave_de_topo_de_mercado_mudou_de_valor` | passa | **REPROVA** |
| 1 | `test_a_rodada_de_adena_nem_CORTA_glifo` | passa | **REPROVA** |
| 5 | `test_o_arquivo_gravado_CARREGA_sem_levantar` | passa | **REPROVA** |
| 5 | `test_a_pagina_da_adena_sai_com_NOVE_linhas_de_taxa` | passa | **REPROVA** |
| 5 | `test_toda_linha_carrega_a_SENTINELA_da_adena` | passa | **REPROVA** |

**5 failed, 4 passed.** E a mensagem da reprovação do caso 1 é o dano, nomeado:

```
AssertionError: uma rodada --layout adena mudou chave de TOPO:
['mercado_ancora', 'mercado_ancoras', 'mercado_cabecalho_de_coluna',
 'mercado_grade', 'mercado_molde_da_ancora']
 — e esta e a calibracao conferida em campo
```

**Honestidade sobre os dois que NÃO reprovaram.** `test_nenhuma_chave_de_topo_DESAPARECEU` e `test_os_TREZE_moldes_de_glifo_continuam_la` **passaram** sob o mutante: nenhuma chave sumiu, e os 13 moldes se fundiram idênticos naquele frame. Eles não são vácuos — prendem verdades diferentes (o CR-04 é exatamente "uma chave sumiu calada") —, mas **não são o discriminante desta mutação**, e ficaria desonesto listá-los como se fossem.

## Verificação — CADA `<automated>` com o resultado REAL

Rodados **exatamente como escritos no plano**.

| Critério | Comando exato | Resultado real |
|---|---|---|
| Task 1 `<automated>` | `pytest tests/test_calibrar_mercado.py tests/test_calibrar_mercado_bat.py -x -q` | **145 passed** |
| Task 2 `<automated>` | `pytest tests/test_calibrar_layout_nao_apaga_negociacao.py -x -q` | **43 passed** |
| `<verification>` linha 1 | `pytest tests/test_calibrar_layout_nao_apaga_negociacao.py -q` | **43 passed** |
| `<verification>` linha 2 | `pytest tests/test_calibrar_mercado.py tests/test_calibrar_mercado_bat.py tests/test_calibrar_nao_apaga_mercado.py tests/test_calibrar_nao_apaga_identidades.py -q` | **163 passed** |

### Nenhum `<automated>` deste plano se revelou vácuo

Os dois discriminam, e o da Task 1 discriminou **de verdade durante a execução**: ele pegou o desvio 1 abaixo (a combinação `--so-digitos --layout adena` que a suíte existente usava) na primeira rodada.

### Pytest — base do worktree e DELTA

- **Base deste worktree, medida ANTES de tocar em nada:** `4185 passed, 24 skipped`
- **Depois:** `4228 passed, 24 skipped`
- **Delta: +43 passed, +0 skipped, 0 falhas** — e 43 é exatamente a contagem do arquivo novo.

`tests/test_janela_de_selecao.py::TestODrenoDaFilaDeTeclas::test_dreno_por_tempo_e_nao_por_numero_de_sondagens` (o que mede relógio em espera ocupada) **não caiu** em nenhuma das duas rodadas cheias.

A referência da main citada no briefing é `4207 passed, 2 skipped`; este worktree pula **22 a mais** (fixturas gitignored), e `4185 + 22 = 4207` — consistente, a mesma explicação que o 05-01 e o 05-02 registraram.

## `<success_criteria>` do plano, um a um

- [x] Uma rodada `--layout adena` deixa toda chave de topo `mercado_*` com valor igual ao de antes, **afirmado sobre o JSON parseado**, com as chaves enumeradas a partir do arquivo de ANTES.
- [x] A mesma rodada grava `mercado_layouts.adena` com cabeçalho (bytes não vazios, contagem batendo com `altura x largura`), limiar em `(0, 1]` e as duas colunas.
- [x] Uma rodada `--layout negociacao` continua alterando as chaves de topo, e para os valores que ELA desenhou.
- [x] `--layout adena` sem grade de negociação recusa **antes de pedir o primeiro arrasto** (`pedidos == []`, medido) e **não reescreve o arquivo**.
- [x] Nenhum teste leu ou escreveu o `calibration.json` da máquina, nem tocou `recordings/`.

## Restrições invioláveis, conferidas

| Restrição | Como foi conferida | Resultado |
|---|---|---|
| não escrever em `calibration.json` (o real) | impressão digital antes/depois — `sha256=0d5e97e787c71382`, `mtime_ns=1788235182304682400`, **12,5 h de idade** (a sessão tem minutos). O arquivo **nem existe dentro do worktree** | **intacto** |
| não escrever em `.mercado/` | mesmo método — 8 arquivos, `mtime_ns` máximo com **2,5 h de idade**; ausente do worktree | **intacto** |
| `VERSAO_DO_ESQUEMA` nunca bumpada | `grep` — segue `= 2`, e o arquivo `mercado_registro.py` não está no diff | **OK** |
| chave nova opcional (`.get`) | nenhuma chave nova foi criada: a escrita usa `mercado_layouts`, que já nasceu opcional no 05-02 | **OK** |
| não tocar `rastreador.py` / gate de brilho em `visao.py` | `git diff --name-only` dos 3 commits | **não aparecem** |
| não tocar `respawn/bosses/agenda/sessao/test_bosses` | `git diff --name-only` dos 3 commits | **não aparecem** |
| `recordings/` somente-leitura, sem glob amplo | não foi lido em momento nenhum; o teste novo não contém a palavra | **OK** |
| nenhuma dependência nova (FIRE-01) | `requirements`/`pyproject` fora do diff | **OK** |
| nenhum `--amend`, nunca `git stash` | — | nenhum dos dois foi usado |

**O `git checkout -- l2scanner/calibrar_mercado.py`** foi usado uma vez, para desfazer a mutação manual num arquivo já commitado — a única operação de descarte permitida, sobre um caminho específico, nunca `git clean` nem reset amplo.

## Accomplishments

- **O portão de escrita por layout.** `args.layout` deixou de ser rótulo e virou destino. O caminho `negociacao` não mudou uma linha de comportamento — os 145 testes da suíte do calibrador são a prova.
- **`_gravar_o_layout_aninhado` não atribui UMA chave de topo.** É a extensão dos dois precedentes de aditividade que já moravam ali (o molde de cabeçalho que só substitui quando houve molde novo; o CR-04) e a docstring cita os dois.
- **A grade sai como DELTA, com a lista importada de quem LÊ.** `CAMPOS_HERDADOS_DA_GRADE` vem de `mercado_pagina`: quem escreve o delta e quem herda usam a mesma lista, e não há segunda cópia para envelhecer. Medido: hoje o delta é **vazio**, e o bloco sai sem `grade` — com controle negativo provando que uma primeira linha de 50 px em vez de 45 **sai gravada** como `{"altura_da_linha": 50, "linhas_por_pagina": 9}`, e que `layout` **não** entra no delta.
- **Três recusas antes do primeiro arrasto**, e as três medidas com `pedidos == []`: sem grade de negociação; com grade de outra aba; com `--so-digitos`; e `busca`, que não tem modelo de coluna medido.
- **Sem molde de cabeçalho, nada é gravado** (T-05-11), com três casos: recusa dizendo por quê, bloco ausente do arquivo, e o topo intacto **também nesse caminho**.
- **A rodada de adena abre 8 janelas em vez de 10, e não digita pergunta nenhuma** — afirmado por igualdade de lista (`["Coluna: total", "Coluna: unitario"]`), nunca por continência, com o controle negativo da negociação pedindo as quatro e digitando.
- **A ida e volta fecha o círculo:** o `calibration.json` que a **ferramenta** gravou carrega por `Calibracao.carregar` e produz as **9 linhas de taxa** de `janela_adena_f014.png`, todas com a sentinela `adena#` — o mesmo número que o 05-02 mediu, mas agora sobre uma calibração que veio da ferramenta e não da fixtura. Controle negativo: sem o bloco, a página é **recusada**.
- **A disciplina do `tmp_path` virou estrutura.** Um fixture autouse desvia `ARQUIVO_CALIBRACAO` para um caminho inexistente dentro de `tmp_path`: um caso futuro que esqueça `--calibracao` estoura com "não encontrei" em vez de ler — ou escrever — a calibração conferida em campo.

## Task Commits

| Task | Commit | O que entrou |
|---|---|---|
| 1 | `f8dbfe2` | o portão de escrita por layout, as recusas, o delta da grade, o resumo reescrito |
| 2 | `f783e68` | os 43 casos, com o arnês que deixa o mutante chegar até a afirmação |
| — | *(final)* | SUMMARY, ROADMAP, REQUIREMENTS |

## Deviations from Plan

### 1. [Rule 1 — o `<automated>` da Task 1 pegou] `TestAPersistenciaDosGlifos` usava a combinação que a Task 1 passou a recusar

- **Encontrado:** na primeira rodada do `<automated>` da Task 1.
- **O que era:** `tests/test_calibrar_mercado.py::TestAPersistenciaDosGlifos` montava o `Namespace` com `layout="adena", so_digitos=True` — os 21 casos da classe. O item 2 do `<action>` manda recusar exatamente essa combinação.
- **Por que o retarget é honesto e não um curativo:** `_calibrar_so_digitos` **não lê `layout` em linha nenhuma** — ele corta glifo, e glifo não carrega coluna. Aquele campo sempre foi decoração naquele caminho; o exemplo era `adena` por acaso. A verdade que a classe prende (o que dos glifos chega ao arquivo e o que nunca chega) não mudou.
- **O que foi feito:** os dois sítios passaram a `layout="negociacao"`, com a razão escrita no fonte, **e a recusa ganhou caso próprio com controle negativo** (`test_so_digitos_fora_da_negociacao_recusa` mais `test_so_digitos_COM_negociacao_continua_valendo`) — sem o par, o retarget poderia estar escondendo uma guarda que nunca dispara.
- **Commit:** `f8dbfe2`.

### 2. [Rule 2 — funcionalidade crítica que o plano não nomeia] `--layout busca` também era uma bomba, e passou a recusar

- **O plano** fala de "layout diferente de negociação" mas só especifica o modelo de coluna da Adena.
- **O problema:** `busca` é um `choice` do CLI desde sempre. Uma tabela `layout -> colunas` sem entrada para ela daria `KeyError`; e deixá-la cair no conjunto da negociação gravaria geometria que leitora nenhuma consome — `busca` está deliberadamente **fora** de `LEITORAS_DE_LINHA_POR_LAYOUT` (05-02, medido por mutação).
- **O que foi feito:** recusa explícita nomeando os layouts que **têm** modelo medido. É estritamente melhor que hoje, onde `--layout busca` marcava as quatro colunas da negociação e gravava o topo — a mesma bomba.

### 3. [Rule 1 — critério meu que quase nasceu vácuo] A semente do teste vai SEM `mercado_layouts`

- **O que o plano pede** no caso 2: semear com uma cópia de `calibracao_de_fixture.json` e afirmar que, depois, `mercado_layouts["adena"]` existe com cabeçalho, limiar e as duas colunas.
- **Por que isso seria vácuo:** a fixtura **já traz** um bloco `adena` — e, medido, **idêntico** ao que a ferramenta produz (`{"total": {"dx": 62, "largura": 209}, "unitario": {"dx": 271, "largura": 174}}`, limiar `0.73`, corte de brilho `222`). O caso passaria com a ferramenta gravando **nada**.
- **O que foi feito:** `_semear` remove `mercado_layouts`, com a razão na docstring e uma asserção de guarda dentro do próprio fixture (`assert "mercado_layouts" not in _ler(alvo)`). É também o estado **real** de toda instalação que existe hoje. Além disso o caso amarra os valores gravados à **entrada desta rodada** (`dx == x - ox`), e não a uma constante.

### 4. [Rule 1 — o arnês estava sendo a rede] As caixas que a rodada não deve pedir ficaram disponíveis

Descrito em detalhe na seção da mutação. Primeira medição do mutante: morreu em `sem sugestao para 'Coluna: nome'`. Um teste cuja rede é o próprio arnês mediu o arnês. Com as caixas disponíveis, o mutante roda até o fim e reprova onde deve.

### 5. [Desvio do `<action>` com razão] Sem molde de cabeçalho a rodada devolve **1**, e não 0

- **O plano diz:** "o bloco NÃO é gravado e a ferramenta diz por quê".
- **O que foi feito:** `MercadoNaoCalibravel`, que imprime limpo e devolve 1 (o `.bat` já trata o `errorlevel`).
- **Por quê:** na negociação o aviso é aviso porque **todo o resto da rodada é gravado**. Numa rodada de layout aninhado não há resto: sem o molde, a rodada produziu **zero**. Devolver 0 diria "deu certo" para uma sessão de marcação que não gravou nada.

### 6. [Ferramenta] `requirements.mark-complete` foi desfeito e refeito à mão

- **O que aconteceu:** o handler marcou os quatro checkboxes corretamente, mas **(a)** inseriu linhas em branco espúrias entre bullets de `DEBT-02..05` e das restrições — churn sem relação com este plano — e **(b)** **não** atualizou a tabela de Rastreabilidade, que continuaria dizendo `Pending` ao lado de um checkbox marcado.
- **O que foi feito:** `git checkout -- REQUIREMENTS.md`, e as duas superfícies atualizadas à mão. Diff final: **16 linhas, 8 pares** — os 4 checkboxes e as 4 linhas da tabela, nada mais.
- **Escopo:** marquei **os quatro** ADEN, e não só os dois do frontmatter deste plano. Os summaries de 05-01, 05-02 e 05-03 deferem explicitamente a "quem fechar a Fase 5"; esta é a onda 3, a última, e as quatro estão entregues com cobertura registrada nos summaries irmãos.

### 7. [Ferramenta — quarta ocorrência do bug documentado] `state.advance-plan` e `state.record-session` NÃO foram executados

- **O briefing documenta três corrupções** do `progress` do milestone ARQUIVADO (`4/4, 21/21, percent 100` virando `1/0, 4/1` sem `percent`), causadas por esses dois handlers, que escrevem mesmo devolvendo `{"error": ...}`.
- **O que foi feito:** os dois foram **deliberadamente pulados**. Rodei apenas `state.update-progress` (que se recusou corretamente, como esperado: `"progress percent withheld by buildStateFrontmatter — STATE.md left unchanged"`) e `roadmap.update-plan-progress 5`.
- **Conferido por impressão digital:** `STATE.md` com `sha256=8fb04f7f885a6d6c` **antes e depois** de toda a sequência de state — **byte a byte inalterado**. O `progress: 4/4, 21/21, percent 100` do milestone arquivado está intacto.

---

**Total deviations:** 7 (2 bugs auto-corrigidos, 1 funcionalidade crítica acrescentada, 2 critérios que teriam nascido vácuos e foram consertados **com o número real medido**, 1 desvio de `<action>` com razão, 1 contorno de bug de ferramenta).
**Impact on plan:** nenhum desvio de escopo. O código entregue é o que o `<action>` das duas tasks descreve.

## Critérios que se revelaram vácuos

**Nenhum dos `<automated>` do plano** — os dois foram rodados exatamente como escritos e os dois discriminam.

**Dois critérios do `<action>` da Task 2 teriam nascido vácuos** e foram consertados antes de fechar, com o número real medido nos dois casos:

1. **O caso 2 sobre a fixtura completa.** A fixtura já traz o bloco `adena` idêntico ao produzido; "existe depois" mediria a semente. Conserto: semente sem a chave, com asserção de guarda. (Desvio 3.)
2. **O arnês como rede.** O mutante morria em `sem sugestao para 'Coluna: nome'` — 4 failed / 3 errors, todos no arnês. Conserto: caixas disponíveis, reprovação passando a vir da afirmação — 5 failed / 4 passed, com as cinco chaves de topo destruídas nomeadas na mensagem. (Desvio 4.)

**Os dois critérios que o briefing proíbe por escrito não foram usados em lugar nenhum**, e a razão está escrita no cabeçalho do arquivo de teste para o próximo leitor não os reintroduzir: `git status --porcelain calibration.json` sai vazio sempre (gitignored, `.gitignore:51` — conferido com `git check-ignore -v`), e `git diff --numstat` sobre não-rastreado idem. Onde precisei afirmar que algo **não** mudou fora do JSON parseado — o `calibration.json` real e o `.mercado/` —, usei **impressão digital de conteúdo (`sha256` + `mtime_ns`)**, o discriminante que a Fase 4 mediu.

## Issues Encountered

Nenhum bloqueio. Nenhum checkpoint.

## Known Stubs

Nenhum. Nenhum valor vazio codificado, texto de placeholder, `TODO` ou `FIXME` no código desta onda. Todo símbolo novo tem consumidor imediato: `COLUNAS_A_MARCAR_POR_LAYOUT` e `FAIXA_DE_CABECALHO_POR_LAYOUT` são lidos por `calibrar` e por `_conferir_a_base_do_layout`; `grade_que_difere_do_topo` e `_gravar_o_layout_aninhado` são chamados por `calibrar`; e a suíte os exercita contra pixels reais.

**Nota de honestidade herdada do 05-02, agora com o número da ferramenta.** O 05-02 registrou que `linhas_por_pagina` herdado vale **10** enquanto `LINHAS_ESPERADAS` do calibrador diz **10** para a adena (e 9 só para a `busca`) — não há conflito, e esta onda confirma: a rodada de adena sobre `janela_adena_f014.png` deriva `linhas_por_pagina: 10` e o delta sai **vazio**. O campo próprio já é suportado e testado (`test_o_CONTROLE_NEGATIVO_uma_grade_diferente_SAI_gravada`).

## Threat Flags

Nenhuma superfície nova além da que o `<threat_model>` do plano já registrava.

- **T-05-10** (DoS: escrita incondicional destruindo a calibração de campo) — **mitigado e MEDIDO**: portão de escrita por layout mais o teste de comparação antes/depois, com a mutação do portão revertido reprovando em 5 casos e nomeando as 5 chaves de topo destruídas.
- **T-05-11** (bloco gravado sem molde de cabeçalho) — **mitigado**: a ferramenta não grava, diz por quê e devolve 1; três casos, incluindo "o topo continua intacto também nesse caminho".
- **T-05-12** (suíte escrevendo no `calibration.json` da máquina) — **mitigado por ESTRUTURA**: fixture autouse desviando `ARQUIVO_CALIBRACAO` para um caminho inexistente em `tmp_path`, além do `--calibracao` por caso. Conferido por impressão digital: o arquivo real tem 12,5 h de idade e nem existe dentro do worktree.

Sem instalação de pacote nesta fase (FIRE-01), conferido.

## Next Phase Readiness

**A Fase 5 fecha aqui.** As quatro ondas entregaram ADEN-01 a ADEN-04, e `REQUIREMENTS.md` foi marcado de uma vez (checkboxes **e** tabela de Rastreabilidade), como os três summaries irmãos pediram.

O que fica registrado para quem vier:

- **`--layout busca` continua sem modelo de coluna medido**, e agora recusa em vez de gravar o topo. Quem quiser a aba precisa medir o modelo dela primeiro; o caminho já está aberto (basta uma entrada em `COLUNAS_A_MARCAR_POR_LAYOUT` mais uma leitora em `LEITORAS_DE_LINHA_POR_LAYOUT`).
- **Pendência herdada do 05-01, não resolvida aqui e não era escopo:** o ramo que aceita arredondamento (`133,33 / 66,66`) segue sem um pixel no repositório.
- **O `deferred-items.md` da fase** (criado pelo 05-03) segue com os quatro itens medidos.
- **O bug do SDK está na quarta ocorrência.** `state.advance-plan` e `state.record-session` escrevem no `STATE.md` mesmo devolvendo erro. Desta vez o dano foi **evitado**, não reparado: os dois não foram executados, e o `sha256` do `STATE.md` é idêntico antes e depois.

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- FOUND `l2scanner/calibrar_mercado.py`
- FOUND `tests/test_calibrar_layout_nao_apaga_negociacao.py`
- FOUND `tests/test_calibrar_mercado.py`

Commits afirmados, conferidos em `git log`:

- FOUND `f8dbfe2`
- FOUND `f783e68`

---
*Phase: 05-a-aba-adena-e-a-taxa-de-cambio*
*Plan: 04*
*Completed: 2026-09-01*
