---
phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
plan: 03
subsystem: renda
tags: [renda, csv, append-only, contrato-de-arquivo, ast-gate, refutacao, tdd, mutacao-de-controle]

requires:
  - phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
    plan: 01
    provides: "`l2scanner/renda_registro.py` INTEIRO — as treze `COLUNAS`, `AUSENCIAS`, `ContratoDaRendaQuebrado`, `conferir_o_terminador` copiada literal, `conferir_o_cabecalho` propria e parametrizada, `campos_da_linha`, `AmostraLida`, `ArquivoRecortado`, `amostras_do_arquivo`, `amostras_ao_vivo`, `RegistroDaRenda` e o LEIAME"
provides:
  - "`tests/test_renda_registro.py` — 53 testes prendendo a superficie de CONTRATO do arquivo `.renda/<personagem>.csv`: o invariante das duas metades nos dois sentidos e para os tres campos, os tres estados do cabecalho com CONTROLE byte a byte, cem amostras identicas em cem linhas, o desligamento definitivo por falha de disco, e a refutacao da C-2 EXECUTAVEL"
  - "A cadeia dos quatro passos da C-2 escrita no fonte, com endereco em cada passo e com as DUAS frases refutadas citadas por linha (`ROADMAP.md:290`, `REQUIREMENTS.md:284`)"
affects: [02-04, workstream dashboard (contrato = o arquivo em disco, e nada alem dele)]

actuals:
  tokens: 13000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Mutacao de CONTROLE rodada contra o proprio teste antes do commit, para provar que o portao e sensivel em vez de decorativo"
    - "Portao de arvore de sintaxe ESCOPADO A UMA FUNCAO pelo nome, com referente absoluto (zero), quando o arquivo inteiro nao tem linha de base"
    - "Refutacao de documento escrita no fonte E presa por teste executavel, para que ela caia em vez de envelhecer em silencio"
    - "Tabela de teste DERIVADA da constante do modulo, com assercao de cobertura que cai quando um campo novo nasce"

key-files:
  created:
    - tests/test_renda_registro.py
  modified:
    - l2scanner/renda_registro.py

key-decisions:
  - "O modulo NASCEU completo no `02-01`, entao Tarefas 1 e 2 sao caracterizacao da superficie de contrato e nao implementacao — e cada portao novo foi validado por MUTACAO antes do commit, porque um teste que passa sobre codigo que ja existia nao prova nada sozinho"
  - "A cadeia da C-2 mora UMA vez so, acima de `ArquivoRecortado`, e o topo do modulo APONTA para ela — duas versoes do mesmo argumento e como uma delas passa a estar errada"
  - "O endereco da frase refutada e o MEDIDO nesta arvore (`ROADMAP.md:290`) e nao o herdado do plano (`274`)"
  - "O teste da falha de disco REMOVE o substituto antes da segunda gravacao: a assercao passa a ser que o registro continua desligado com o disco de volta, e nao so que ele devolveu falso"
  - "O portao do `except OSError` ganhou CONTROLE POSITIVO: um `AttributeError` de refatoracao tem de SUBIR, e nao virar 'conserte o arquivo ou a pasta'"

requirements-completed: [REG-01, REG-02, REG-03, REG-04, REND-04]

coverage:
  - id: E1
    description: "Para cada um dos tres campos, EXATAMENTE uma das duas metades esta preenchida — nas duas direcoes"
    requirement: REG-01
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestOInvarianteDasDuasMetades (11 testes, 2 parametrizados por 3 campos)"
        status: pass
    human_judgment: false
  - id: E2
    description: "Gravar cem amostras identicas produz cem linhas — a dedup do mercado nao atravessou, nem por identidade nem por janela (C-3)"
    requirement: REG-03
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestADedupQueNaoAtravessou (3 testes: duas, cem, e o portao de AST do construtor)"
        status: pass
    human_judgment: false
  - id: E3
    description: "Contrato quebrado desliga a feature alto e NAO altera um byte do arquivo do usuario"
    requirement: REG-01
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestOsTresEstadosDoCabecalho::test_CONTROLE_O_DIVERGENTE_NAO_ALTERA_UM_BYTE + ::TestOPortaoDoTerminador (3 testes)"
        status: pass
    human_judgment: false
  - id: E4
    description: "As recusas tambem viram linha, com o motivo por campo e a guarda ao lado do valor (CTX-9, LEIT-11)"
    requirement: REG-01
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestAsRecusasTambemSaoGravadas (2 testes)"
        status: pass
    human_judgment: false
  - id: E5
    description: "Um arquivo por personagem, dois personagens nunca se misturam, e um nome hostil nunca sai da pasta (C-5, T-02-17)"
    requirement: REG-04
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestUmArquivoPorPersonagem (4 testes, 3 nomes hostis por Path.resolve())"
        status: pass
    human_judgment: false
  - id: E6
    description: "`origem_do_ganho` sai `indeterminado` em TODA linha, e nenhum limiar decide esse valor onde ele e decidido"
    requirement: REND-04
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestAOrigemDoGanho (2 testes: comportamental + portao de AST escopado a `campos_da_linha`)"
        status: pass
    human_judgment: false
  - id: E7
    description: "Disco cheio derruba o registro da renda e nunca os alertas de morte da party; o desligamento e definitivo e sem nova tentativa (T-02-19)"
    requirement: REG-01
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestOAppendEAFalhaDeDisco (5 testes, com o CONTROLE do `except OSError`)"
        status: pass
    human_judgment: false
  - id: E8
    description: "A frase 'uma lista de colunas, nao um parser' caiu — escrita no fonte com os quatro passos e presa por teste que aponta o parser do mercado para um CSV de renda (C-2)"
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestARefutacaoDaC2 (4 testes) + ::TestONaoImportarDoDashboard (2 testes)"
        status: pass
    human_judgment: false
  - id: E9
    description: "O leitor tolerante corta na ultima linha completa e os dois portoes continuam sendo chamados DEPOIS do corte"
    requirement: REG-02
    verification:
      - kind: unit
        ref: "tests/test_renda_registro.py::TestOLeitorTolerante (8 testes, com o de equivalencia entre a rota do recorte e a chamada direta)"
        status: pass
    human_judgment: false

duration: 38min
completed: 2026-09-02
status: complete
---

# Fase 2 Plano 03: O registro em `.renda/` — Summary

**As treze colunas do `.renda/<personagem>.csv` viraram contrato preso por 53 testes — cem amostras identicas deixando cem linhas, o cabecalho divergente sem um byte alterado, e a frase "o dashboard acrescenta uma lista de colunas, nao um parser" refutada no fonte com os quatro passos da cadeia e derrubada por um teste que aponta o parser do mercado para um CSV de renda.**

## Performance

- **Duration:** ~38 min
- **Tasks:** 3 de 3
- **Files created:** 1 · **Files modified:** 1
- **Suite:** 5508 passed / 24 skipped (linha de base desta arvore) -> **5561 passed / 24 skipped**, sempre com `--ignore=tests/test_agenda.py`
- **Testes acrescentados:** 53, zero `skip`

## O fato que muda como este plano deve ser lido

**`l2scanner/renda_registro.py` nao estava pela metade: ele NASCEU COMPLETO no `02-01`**, com 998 linhas, os dois portoes, o escritor, o leitor tolerante e o LEIAME. O `02-01-SUMMARY.md` diz isso na secao "Contratos que a onda 2 herda", e a superficie listada ali estava toda em disco.

Entao as Tarefas 1 e 2 deste plano **nao foram implementacao — foram caracterizacao da superficie de contrato**, e os testes passaram na primeira execucao. Isso e um risco real: um teste que passa sobre codigo que ja existia nao prova que ele e sensivel; ele pode estar afirmando uma tautologia. **A resposta foi rodar MUTACAO DE CONTROLE contra cada portao novo antes de comitar**, e as tres estao registradas abaixo com o resultado.

A unica RED de codigo genuina foi a Tarefa 3, e ela esta no commit `22bbb24` com dois testes falhando de proposito.

## Task Commits

| # | Tarefa | Commit | Tipo |
|---|---|---|---|
| 1 | O invariante das duas metades e os tres estados do cabecalho | `873f273` | test |
| 2 | Cem amostras identicas em cem linhas, e o desligamento que nao volta | `95931ae` | test |
| 3 RED | A refutacao da C-2 cobrada do fonte (2 testes falhando) | `22bbb24` | test |
| 3 GREEN | A cadeia dos quatro passos, com endereco em cada um | `a8cc27f` | feat |

Nenhum commit de REFACTOR: o bloco novo saiu no formato final e nao havia o que limpar.

## As tres mutacoes de controle

Cada uma foi enxertada no fonte, a suite rodada, e o fonte restaurado do backup. **Nenhuma delas esta na arvore** — `git status` limpo depois de cada uma.

| Mutacao enxertada | Testes que caem | O que isso prova |
|---|---|---|
| `_celulas_do_campo` passa a devolver `("", "0", motivo)` — guarda preenchida num campo RECUSADO | 3 (o invariante parametrizado nos tres campos) | O teste ve a metade errada preenchida, e nao so "o motivo existe" |
| `registrar` ganha `if self._ultima == chave: return True` — uma dedup por janela | 5, entre eles os de duas e de cem amostras | O portao da C-3 pega dedup por JANELA e nao so por identidade de linha |
| O `self.ligado = False` some do `except OSError` — retry por tique | 1 (`test_FALHA_DE_ESCRITA_DESLIGA_A_SESSAO_INTEIRA_SEM_NOVA_TENTATIVA`) | O teste distingue "devolveu falso" de "parou de tocar o disco" |

Sem estas tres, este plano teria entregue 53 testes verdes sobre codigo que ja passava — e nenhuma evidencia de que algum deles pegaria alguma coisa.

## As tres afirmacoes medidas, e onde cada uma ficou presa

### C-3 — a dedup que nao atravessou, e por que o portao vem em DUAS escalas

`mercado_registro.chave_da_observacao` exclui o carimbo de proposito. Aqui uma linha por tique **e o produto** — ela e o denominador da taxa.

O portao de **duas** amostras identicas ja existia no tracer do `02-01`. Ele **nao basta**: uma dedup "no maximo uma linha por minuto" ou "so grava quando mudou desde a ultima" passaria com duas amostras espacadas de 30 s. O portao de **cem** amostras a 1 Hz e o caso real do personagem parado — a adena so muda quando cai loot — e e ele que cai na mutacao. Os dois juntos, e o portao de AST do construtor (`ast.Set`/`ast.SetComp`) ao lado, que pega o indice sendo montado antes de alguem usa-lo.

### C-2 — a refutacao virou argumento, e nao conclusao

O que o `02-01` deixou era uma frase: *"o que refuta a frase 'o dashboard acrescenta uma lista de colunas, nao um parser'"*. Faltavam o argumento e o endereco da frase refutada.

O bloco novo, imediatamente acima de `ArquivoRecortado`, escreve os **quatro passos** com endereco em cada um:

1. `dashboard_dados.observacoes_ao_vivo:454` chama o parser do mercado **por nome** — sem parametro, sem registro de parsers, sem ponto de injecao.
2. Aquele parser confere o cabecalho contra o `COLUNAS` **global** (`mercado_registro.py:495`), e um CSV de renda **levanta na primeira linha**.
3. O laco de tipagem monta `ObservacaoLida` com `COLUNAS.index(...)` e `residuo_dos_campos` — mercado puro.
4. Acima disso, `payload` e `ModeloDeMercado`, cambio e cinco estados.

E as duas frases refutadas vao citadas por linha: `ROADMAP.md:290` e `REQUIREMENTS.md:284`.

**E o teste executavel ao lado**, que e o ponto: `test_O_PARSER_DO_MERCADO_APONTADO_PARA_UM_CSV_DE_RENDA_LEVANTA` escreve um `.renda/` real com o escritor desta fase, aponta `mercado_registro.observacoes_do_arquivo` para ele, e afirma `ContratoDoArquivoQuebrado`. Se alguem parametrizar o cabecalho do mercado, **este teste cai** — e a prosa e reescrita em vez de continuar mentindo por anos.

O portao de "nao importar do `dashboard`" e por **arvore de sintaxe** e nunca por `grep`, e a razao esta escrita no proprio teste: este fonte **tem** de citar `dashboard_dados.py:454` para explicar a C-2, entao um portao de texto acusaria a propria refutacao e se contradiria com o criterio que a exige.

### C-5 — um arquivo por personagem, sem rotacao por data

A razao e **concorrencia e nao precedente**: o usuario roda duas instancias e o dialeto copiado pressupoe um escritor por arquivo (`mercado_registro.py:607`). Rotacao por data alem disso obrigaria o leitor a decidir a virada da meia-noite no meio de uma janela movel de dez minutos, criando uma lacuna artificial indistinguivel de uma real.

O teste de dois personagens afirma as tres coisas juntas: dois arquivos, nenhuma linha de um no outro, e a coluna `personagem` de cada linha batendo com o `stem` do arquivo em que ela esta. Os tres nomes hostis sao comparados por `Path.resolve()` contra a pasta resolvida — um teste que so procurasse `".."` no nome passaria com um separador exotico.

## O portao da origem, e por que ele ficou escopado

O plan-checker rescopou este portao, e a razao vai repetida no fonte do teste para nao voltar:

A versao anterior contava as comparacoes do **arquivo inteiro** e mandava afirmar que o numero *"nao cresceu por causa da origem"*. **Nao existe referente para "nao cresceu"**: o modulo nasce no `02-01` e expande aqui, entao qualquer numero que o executor medisse seria carimbado como linha de base sem ninguem saber contra o que — e um portao cujo valor esperado o proprio executor escolhe nao e portao.

O escopo por funcao tem referente **absoluto — zero** — e diz mais: a origem nao pode sair de limiar porque no lugar onde ela e decidida (`campos_da_linha`) nao ha limiar nenhum. `is`, `==` e `!=` continuam legitimos ali; o portao olha so comparacao de **ordem**. E ele afirma tambem que a funcao **existe e e uma so**, porque duas definicoes fariam a varredura olhar uma delas e passar.

## Deviations from Plan

Nenhum auto-fix de codigo. Tres correcoes de referente no plano, e uma constatacao de escopo.

**1. [Rule 1 - Referente errado] O nome da excecao e `ContratoDaRendaQuebrado`, e nao `ContratoDoArquivoDeRendaQuebrado`**

- **Found during:** Tarefa 1, ao montar o portao de aceitacao.
- **Issue:** o criterio do plano manda conferir `r.ContratoDoArquivoDeRendaQuebrado`. Esse simbolo nao existe: o `02-01` batizou a excecao de `ContratoDaRendaQuebrado` e a declarou como contrato herdado pela onda 2, na secao "Contratos que a onda 2 herda" do `02-01-SUMMARY.md`.
- **Fix:** o portao usa o nome real. **A semantica exigida ficou intacta e foi conferida**: `ContratoDaRendaQuebrado is mercado_registro.ContratoDoArquivoQuebrado` -> `False`, e `issubclass(...)` -> `False`. Os dois `False` que o criterio pedia.
- **Files modified:** nenhum. Renomear a excecao quebraria o contrato de onda com o `02-04`, que a importa pelo nome.

**2. [Rule 1 - Referente errado] A frase refutada esta em `ROADMAP.md:290`, e nao em `:274`**

- **Found during:** Tarefa 3, ao escrever a citacao por endereco.
- **Issue:** `ROADMAP.md:274` nao contem a frase — ali esta o criterio 4 da fase. A frase *"acrescentando uma lista de colunas, nao um parser"* esta na **linha 290**, e ha uma segunda ocorrencia na 330. `REQUIREMENTS.md:284` esta correto.
- **Fix:** o fonte cita o endereco **medido** nesta arvore. Um endereco errado numa refutacao e pior que nenhum: manda a proxima pessoa para o lugar errado e ela conclui que a refutacao envelheceu.
- **Files modified:** `l2scanner/renda_registro.py` (o bloco da C-2).

**3. [Rule 1 - Medicao errada no criterio] A linha de base e `5508 passed`, e o `5355` / `5532` sao totais SELECIONADOS**

- **Found during:** antes da Tarefa 1.
- **Issue:** e a **mesma** conflacao que o `02-01-SUMMARY.md` ja registrou uma vez. O plano diz "o total de `passed` nao cai abaixo de **5355**"; o prompt de execucao diz **5532**. Medido nesta arvore, no estado de partida: **5508 passed, 24 skipped**. E `5508 + 24 = 5532` — o numero do prompt e o total **selecionado** (passed + skipped), exatamente como o `5355` era o selecionado da arvore anterior.
- **Fix:** nada foi enfraquecido. O piso e conferido nas **duas metades**, que e o que o piso existe para fazer: `passed >= 5508` **e** `passed + skipped >= 5532`. Resultado final: **5561 passed / 24 skipped** = 5585 selecionados. As duas passam com folga, e o criterio na letra (`>= 5355`) tambem.
- **Files modified:** nenhum. Registrado aqui e em `.planning/WINDOWS.md`, como o prompt indicou.

**4. [Nao e deviacao — e constatacao de escopo] As Tarefas 1 e 2 nao tinham RED possivel**

O modulo nasceu completo no `02-01`. Um "RED" fabricado — apagar codigo funcionando para reescrever igual — seria teatro e arriscaria a superficie de contrato que o `02-04` ja importa. O que foi feito no lugar esta na secao "As tres mutacoes de controle": cada portao novo foi provado sensivel por mutacao antes do commit. Isso e mais forte que um RED encenado, porque prova o que o RED prova (o teste falha quando o comportamento e outro) sem tocar o codigo que ja funciona.

---

**Total deviations:** 3 correcoes de referente, 0 auto-fix de codigo, 0 mudanca arquitetural, 0 portao afrouxado.

## Issues Encountered

- **`renda_registro.py` ter nascido completo mudou a natureza do plano no meio.** O plano foi escrito supondo que o `02-01` deixaria a fatia e este plano fecharia o arquivo; o `02-01` fechou o arquivo. A escolha foi tratar as Tarefas 1 e 2 como caracterizacao com mutacao de controle, em vez de reescrever o modulo para fabricar um RED. Isso esta escrito acima e nao no rodape porque quem ler o proximo plano precisa saber que a superficie de contrato ja esta congelada desde a onda 1.
- **O portao "sem import de `dashboard`" e a exigencia "cite `dashboard_dados.py:454`" se contradizem se o portao for de texto.** Resolvido com AST, e a razao ficou escrita no proprio teste para que ninguem "simplifique" o portao para um `grep` depois.

## Known Stubs

Nenhum. Nenhum valor vazio codificado, nenhum `TODO`, nenhum `FIXME`, nenhum `placeholder`, nenhum `skip`.

`origem_do_ganho = "indeterminado"` **nao e stub** e ja estava assim registrado no `02-01`: e a decisao CTX-7 escrita (farm x venda por marcador explicito, nunca heuristica), com a razao no fonte, no LEIAME e agora presa por dois testes — um comportamental afirmando o valor em **toda** linha inclusive nas de recusa, e um portao de AST afirmando que **nenhum** limiar decide esse valor no lugar onde ele e decidido.

## Threat Flags

Nenhuma superficie nova. As sete ameacas `mitigate` do `<threat_model>` deste plano ficaram cobertas:

| ID | Mitigacao | Onde esta presa |
|---|---|---|
| T-02-14 | `conferir_o_terminador` copiada literal | `TestOPortaoDoTerminador` (3 testes, com o CONTROLE de que o arquivo continua sem a quebra) |
| T-02-15 | Portao do cabecalho, tres estados, nunca migrar | `TestOsTresEstadosDoCabecalho` (6 testes, com o CONTROLE byte a byte) |
| T-02-16 | Sem conjunto, sem indice, sem funcao de identidade | `TestADedupQueNaoAtravessou` (3 testes) + mutacao de controle |
| T-02-17 | `apelido()` por lista de PERMISSAO, pasta de `RAIZ` | `test_UM_NOME_HOSTIL_NAO_SAI_DA_PASTA` (3 nomes, por `Path.resolve()`) |
| T-02-18 | Corte antes do portao, sinal de cauda separado | `TestOLeitorTolerante` (8 testes) |
| T-02-19 | `except OSError` e so, desligamento definitivo | `TestOAppendEAFalhaDeDisco` (5 testes, com CONTROLE positivo do `AttributeError`) |
| T-02-20 | As recusas gravadas com motivo, guarda ao lado do valor | `TestAsRecusasTambemSaoGravadas` (2) + `TestOInvarianteDasDuasMetades` (11) |
| T-02-SC | Nenhum `pip install` | `git diff --stat requirements.txt` vazio |

## Verification Results

| Criterio | Resultado |
|---|---|
| `pytest tests/test_renda_registro.py -q` termina em 0 com 0 skipped | **53 passed, 0 skipped** |
| `pytest tests/test_renda_registro.py tests/test_renda_conta_tracer.py -q` | **82 passed, 0 skipped** |
| `pytest --ignore=tests/test_agenda.py -q` e `passed` nao cai | **5561 passed / 24 skipped** (base: 5508 / 24) |
| `git diff --stat requirements.txt` vazio | vazio |
| `git status --porcelain` sem `l2scanner/renda_conta.py` e sem `l2scanner/dashboard*` | limpo — os commits tocam so `renda_registro.py` e o teste |
| `git status --porcelain .mercado/` vazio | vazio |
| `ContratoDaRendaQuebrado` e propria e nao herda | `False False` |
| `conferir_o_cabecalho` importado do mercado | `[]` |
| `fromtimestamp` no modulo | `1` |
| `now`/`time` chamados no modulo | `[]` |
| imports com `dashboard` no nome | `[]` |
| `campos_da_linha` — quantas, e limiares de ordem dentro | `1 []` |
| `ast.Set`/`ast.SetComp` no `__init__` | `[]` |
| `cv2`, `numpy`, `dashboard_dados` apos importar o modulo | `False False False` (116 modulos) |
| `grep -c "lista de colunas"` | `2` |
| `ROADMAP.md:290`, `REQUIREMENTS.md:284`, `dashboard_dados.py:454`, `mercado_registro.py:495` no fonte | os quatro presentes |

## Self-Check: PASSED

Arquivos conferidos em disco: `tests/test_renda_registro.py` (novo, 1141 linhas) e `l2scanner/renda_registro.py` (modificado, +47 linhas) — os dois presentes.

Commits conferidos em `git log`: `873f273`, `95931ae`, `22bbb24`, `a8cc27f` — os quatro presentes. `git diff --diff-filter=D` vazio nos quatro: nenhuma delecao de arquivo.
