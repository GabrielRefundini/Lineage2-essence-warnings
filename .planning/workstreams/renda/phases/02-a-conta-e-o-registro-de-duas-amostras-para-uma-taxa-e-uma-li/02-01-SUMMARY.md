---
phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
plan: 01
subsystem: renda
tags: [renda, csv, append-only, config-toml, gitignore, fraction, ast-gate, tdd]

requires:
  - phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
    provides: "`LeituraDaRenda`, `CamposDaRenda`, `ValorDaRenda`, `ValorDaAdena`, `RecusaDaRenda`, `DECIMOS_DE_MILESIMO_POR_PONTO` e as quatro regras de par (`o_exp_andou_para_tras`, `o_nivel_andou_para_tras`, `a_adena_saltou_ordem_de_grandeza`, `conferir_o_par`) — escritas puras e ate hoje SEM chamador de producao, por desenho"
provides:
  - "`l2scanner/renda_conta.py` — `PassoDaRenda`, `passo_entre`, `TaxaDaRenda`, `taxa_por_hora`; o UNICO chamador de producao das regras de par de toda a arvore"
  - "`l2scanner/renda_registro.py` — as treze `COLUNAS` de `.renda/<personagem>.csv`, `conferir_o_terminador` copiada literal, cabecalho-contrato proprio e parametrizado, escritor append-only sem dedup, leitor tolerante com corte de cauda, e o LEIAME"
  - "`config.AjustesDaRenda` e `ler_ajustes_da_renda` — os cinco numeros da secao `[renda]`, com defaults na casca e validacao de arranque"
  - "O portao INVERTIDO de `tests/test_renda_par.py`: `chamadores_das_regras` como funcao de modulo, exigindo chamador que existe, que e UM SO e que chama a composicao"
  - "`.renda/` no `.gitignore`, com a razao escrita ao lado"
affects: [02-02, 02-03, 02-04, workstream dashboard (contrato = o arquivo em disco)]

actuals:
  tokens: 37000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Import diferido de modulo pesado dentro da funcao que o usa, com o custo MEDIDO na docstring"
    - "Portao de arvore de sintaxe INVERTIDO em vez de apagado, com a transicao contada na docstring"
    - "Delta de tempo com o sinal preservado — `abs`/`max`/`min` proibidos por portao de AST"
    - "Taxa que carrega `Evidencia`, janela, unidade, lacunas e recencia SEPARADA do valor"

key-files:
  created:
    - l2scanner/renda_conta.py
    - l2scanner/renda_registro.py
    - tests/test_renda_conta_tracer.py
    - tests/test_config_da_renda.py
  modified:
    - tests/test_renda_par.py
    - l2scanner/config.py
    - config.toml
    - .gitignore

key-decisions:
  - "UM ARQUIVO POR PERSONAGEM, sem rotacao por data (C-5) — o usuario roda duas instancias, e um arquivo so teria dois escritores concorrentes; uma linha entrelacada passa no portao do terminador"
  - "O import de `renda_leitura` em `renda_conta` e DIFERIDO (dentro de `passo_entre`) porque ele traz 334 modulos com cv2 e numpy — medido; a definicao continua uma so"
  - "`Evidencia` e IMPORTADA de `mercado_analise` (102 modulos, sem cv2/numpy — medido), e nao redefinida"
  - "`AjustesDaRenda` nasce em `config.py` e nao no modulo puro — a seta aponta casca -> puro, e declara-lo no puro obrigaria `renda_conta` a importar `config` -> `notificador` -> `rastreador` -> `visao` -> `cv2`"
  - "A dedup do `mercado_registro` NAO foi copiada: aqui uma linha por tique E o produto, e ela e o denominador da taxa"
  - "Passo de lacuna perde o ganho JUNTO com o tempo — guardar o ganho e descartar o intervalo poria o numerador de meia hora num denominador de dez minutos"
  - "`RegistroDaRenda` e classe comum e nao `dataclass`, para que o portao de AST sobre `__init__` varra codigo de verdade em vez do vazio"

patterns-established:
  - "Escape hatch de import medido: se o import no topo arrasta cv2/numpy, ele desce para dentro da funcao, com o numero medido escrito ao lado — nunca uma segunda definicao"
  - "Portao de AST que afirma TRES coisas na mesma funcao, porque cada uma sozinha passaria com o desenho errado (lista vazia satisfaz 'o conjunto e X' e 'o nome e Y')"
  - "Constantes de ausencia (`AUSENCIAS`) derivadas pelo teste do proprio modulo, para que uma lista escrita a mao no teste nao envelheca em silencio"

requirements-completed: [REND-01, REND-02, REND-06, REG-01, REG-03, REG-04]

coverage:
  - id: D1
    description: "Duas amostras montadas a mao atravessam regras de par, passo, disco, leitor tolerante e taxa por hora num caminho so"
    requirement: REND-01
    verification:
      - kind: integration
        ref: "tests/test_renda_conta_tracer.py::TestAFatiaDePontaAPontaComOParOrdinario::test_DUAS_AMOSTRAS_ATRAVESSAM_REGRAS_PASSO_DISCO_E_TAXA"
        status: pass
    human_judgment: false
  - id: D2
    description: "O par de campo do level up sai com ganho de EXP 394_380 decimos, e nunca -605_620"
    requirement: REND-02
    verification:
      - kind: unit
        ref: "tests/test_renda_conta_tracer.py::TestOParDeCampoDoLevelUpPelaFatiaInteira (2 testes: o valor e o CONTROLE contra o negativo/zero)"
        status: pass
    human_judgment: false
  - id: D3
    description: "O portao da Fase 1 INVERTIDO: chamador que existe, que e um so (renda_conta.py) e que chama conferir_o_par, com dois controles positivos"
    verification:
      - kind: unit
        ref: "tests/test_renda_par.py::TestOPortaoDoChamadorDeProducao (5 testes)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A taxa nunca e numero nu: Evidencia, janela farmada, unidade `minutos farmados`, lacunas excluidas e recencia separada"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta_tracer.py::TestATaxaNuncaEUmNumeroNu + ::TestATaxaComLacunaESemLacuna"
        status: pass
    human_judgment: false
  - id: D5
    description: "Abaixo de qualquer um dos dois pisos a resposta e o MOTIVO nomeado e nunca um numero"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta_tracer.py::TestOsDoisPisos (3 testes, incluindo o CONTROLE que estende acima do piso)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Cada amostra vira uma linha append-only em `.renda/<personagem>.csv` no dialeto do `.mercado/`, com as treze colunas"
    requirement: REG-01
    verification:
      - kind: integration
        ref: "tests/test_renda_conta_tracer.py::TestAIdaEVoltaPeloDisco (4 testes) + ::TestOLeitorTolerante (3 testes)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Gravar duas amostras identicas produz DUAS linhas — a dedup do mercado nao atravessou (C-3)"
    requirement: REG-03
    verification:
      - kind: unit
        ref: "tests/test_renda_conta_tracer.py::TestAIdaEVoltaPeloDisco::test_DUAS_AMOSTRAS_IDENTICAS_DEIXAM_DUAS_LINHAS"
        status: pass
    human_judgment: false
  - id: D8
    description: "Os cinco numeros moram na secao `[renda]` do config.toml, com defaults na casca e nenhum valor de fabrica no modulo puro"
    requirement: REG-04
    verification:
      - kind: unit
        ref: "tests/test_config_da_renda.py (41 testes) + tests/test_renda_conta_tracer.py::TestNenhumLimiarTemValorDeFabrica"
        status: pass
    human_judgment: false
  - id: D9
    description: "`.renda/` esta fora do repositorio com a razao escrita ao lado, e o LEIAME nasce com a pasta e nunca sobrescreve a anotacao do usuario"
    requirement: REG-04
    verification:
      - kind: unit
        ref: "tests/test_renda_conta_tracer.py::TestOLeiameQueNasceJuntoComAPasta (5 testes)"
        status: pass
      - kind: other
        ref: "git check-ignore -v .renda/ && git check-ignore -v .renda/Faerlina.csv"
        status: pass
    human_judgment: false

duration: 71min
completed: 2026-09-02
status: complete
---

# Fase 2 Plano 01: A fatia fina da conta e do registro — Summary

**Duas `LeituraDaRenda` montadas a mao atravessam as regras de par da Fase 1, o passo com o delta, uma linha append-only em `.renda/`, o leitor tolerante e saem como taxa por hora com `n` — e o portao que proibia esse caminho foi invertido no mesmo commit em que o caminho nasceu.**

## Performance

- **Duration:** ~71 min
- **Tasks:** 3 de 3
- **Files created:** 4 · **Files modified:** 4
- **Suite:** 5331 passed / 24 skipped (linha de base) -> **5406 passed / 24 skipped**, sempre com `--ignore=tests/test_agenda.py`

## Accomplishments

- **A C-1 executada como o plano mandou.** `tests/test_renda_par.py:591-623` proibia qualquer modulo de `l2scanner/` de chamar as regras de par. A varredura foi EXTRAIDA para a funcao de modulo `chamadores_das_regras(raiz)` — e a extracao nao e arrumacao, e o que permite ao controle positivo chamar a MESMA funcao do portao —, e o portao passou a afirmar **tres coisas na mesma funcao**: que a lista nao esta vazia, que o conjunto de modulos chamadores e exatamente `{renda_conta.py}`, e que o nome chamado e `conferir_o_par`. Dois controles positivos com `tmp_path`: dois modulos sinteticos acusados **pelos dois nomes e pelos dois estilos de chamada** (nome nu e atributo), e uma arvore sem chamador devolvendo lista vazia. O teste antigo nao sobreviveu ao lado do novo, e ha um teste de AST afirmando isso.
- **O par de campo do level up atravessa a fatia inteira** e sai `394_380` decimos de milesimo — os 39,438 pontos percentuais medidos na tela —, com o CONTROLE ao lado afirmando que ele nao e o `-605_620` da subtracao ingenua **nem zero**, porque um `max(0, ...)` em cima do ingenuo passaria no primeiro teste.
- **A taxa nunca e um numero nu.** `Evidencia` viaja dentro, `por_hora` e `None` quando nao ha numero a dizer, `motivo_da_ausencia` diz QUAL dos dois pisos faltou, `janela_farmada_em_segundos` e o denominador real, `lacunas_excluidas`/`segundos_em_lacuna` sao os dois fatos que sairam dele, `ate` e a recencia separada, e `unidade_da_janela` viaja escrita — `minutos farmados`.
- **A exclusao da lacuna esta provada por IGUALDADE EXATA e nao por tolerancia:** 21 amostras a cada 30 s dao a mesma taxa por hora que as mesmas 21 amostras com um buraco de 20 minutos no meio (`120_000` decimos/h nas duas), com `lacunas_excluidas == 1` e `segundos_em_lacuna == 1230.0`.
- **A dedup do mercado NAO atravessou**, e ha portao comportamental: duas amostras com `nivel`, `exp` e `adena` identicos e carimbos diferentes deixam **duas** linhas. Copiar a dedup teria apagado a maioria das linhas de uma noite de farm — a adena so muda quando cai loot.
- **Os cinco numeros moram no `config.toml`** com uma razao por chave (442 -> 519 linhas de comentario), a secao entra COMENTADA como a `[identidade]`, e nenhum dos limiares tem valor de fabrica no modulo puro.
- **Nenhuma dependencia nova, nenhum arquivo do workstream `dashboard` tocado, e `import l2scanner.renda_conta, l2scanner.renda_registro` traz 129 modulos sem `cv2` e sem `numpy`.**

## Task Commits

1. **Tarefa 1: A fatia + a inversao do portao (tracer)** — `c3af35a` (feat)
2. **Tarefa 2 RED: a secao `[renda]` falhando antes de existir** — `8e48b3a` (test)
3. **Tarefa 2 GREEN: os cinco numeros no `config.toml`** — `e9e2cbc` (feat)
4. **Tarefa 3: `.renda/` no `.gitignore` + o LEIAME preso por teste** — `15815de` (feat)

Nenhum commit de REFACTOR: a implementacao da Tarefa 2 saiu do molde literal de `ler_ajustes_do_aprendiz` e nao havia o que limpar.

## Files Created/Modified

- `l2scanner/renda_conta.py` (novo) — o modulo puro. `PassoDaRenda`, `passo_entre`, `TaxaDaRenda`, `taxa_por_hora`. Sem disco, sem relogio, sem `abs`/`max`/`min`.
- `l2scanner/renda_registro.py` (novo) — as treze `COLUNAS` com as quatro ausencias em bloco de comentario, a excecao propria `ContratoDaRendaQuebrado`, `conferir_o_terminador` copiada literal, `conferir_o_cabecalho` propria e parametrizada, `arquivo_do_personagem` via `apelido()`, `campos_da_linha`, `AmostraLida`, `ArquivoRecortado`, `amostras_do_arquivo`, `amostras_ao_vivo`, `RegistroDaRenda` e o `TEXTO_DO_LEIAME`.
- `tests/test_renda_conta_tracer.py` (novo) — 29 testes de ponta a ponta, zero `skip`, zero dependencia de OCR/pixel/rede.
- `tests/test_config_da_renda.py` (novo) — 41 testes da secao `[renda]`.
- `tests/test_renda_par.py` — o portao invertido, `chamadores_das_regras`, dois controles positivos, e `memoria_de_modulo` estendida aos dois modulos novos.
- `l2scanner/config.py` — `SECAO_DA_RENDA`, as cinco chaves, `AjustesDaRenda`, `_EXEMPLO_DA_RENDA`, `_inteiro_da_renda`, `ler_ajustes_da_renda`.
- `config.toml` — a secao `[renda]` comentada.
- `.gitignore` — `.renda/`, com cinco linhas de razao acima dela.

## Decisions Made

Alem das cinco escolhas que o plano ja tinha decidido (forma do arquivo, os cinco numeros no `config.toml`, `float` epoch na aritmetica, sessao delimitada por lacuna, treze colunas), estas foram decididas na execucao:

1. **O import de `renda_leitura` dentro de `renda_conta` e DIFERIDO, e nao no topo.** Medido nesta arvore: `import l2scanner.renda_leitura` traz **334 modulos, com `cv2` E `numpy`** (ele importa `mercado_visao` e `ocr`, que sao a metade de PIXEL da Fase 1). O criterio de aceitacao do plano exige que `import l2scanner.renda_conta` nao traga nenhum dos dois. As duas exigencias so se conciliam com o import descendo para dentro de `passo_entre`, que e a unica funcao que precisa dele. A doutrina de "importados, e nao redefinidos" fica inteira — a definicao de `conferir_o_par` e de `DECIMOS_DE_MILESIMO_POR_PONTO` continua uma so, ela so nao e paga no topo. Escrito na docstring do modulo com o numero medido.
2. **`Evidencia` foi IMPORTADA e nao duplicada.** O plano autorizava uma irma local "se o import arrastar `cv2` ou `numpy`". Medido: `import l2scanner.mercado_analise` traz **102 modulos, sem os dois**. A irma local nao era necessaria, e uma segunda `Evidencia` seria duas definicoes do mesmo conceito.
3. **`RegistroDaRenda` e classe comum e nao `dataclass`.** O criterio de aceitacao varre o `__init__` do modulo procurando `ast.Set`/`ast.SetComp` — o sinal de alerta de que a dedup atravessou. Um `dataclass` nao teria `__init__` no fonte e o portao varreria o vazio, passando **por construcao** em vez de por medicao. A razao esta escrita no proprio construtor.
4. **Um passo de lacuna perde o GANHO junto com o TEMPO.** O plano decidiu que o tempo cego sai do denominador; nao dizia explicitamente o que fazer com o numerador daquele passo. Guardar o ganho e descartar o intervalo poria o numerador de meia hora num denominador de dez minutos — uma taxa inventada. Os dois saem juntos, e e o que faz a igualdade exata do teste da lacuna funcionar.
5. **`amostras_ao_vivo` LEVANTA num arquivo nao vazio sem uma unica quebra de linha**, divergindo deliberadamente de `dashboard_dados.observacoes_ao_vivo`, que degrada. La quem le e um painel de so-leitura que tem de degradar para nao ficar mudo; aqui o mesmo arquivo e do ESCRITOR, e um arquivo sem uma linha completa nao tem nem cabecalho. A divergencia esta escrita na docstring e o criterio de aceitacao do plano pedia exatamente este comportamento.
6. **`janela_movel_minutos` entra lido e conferido mas AINDA SEM CONSUMIDOR**, e isso vai escrito no `config.toml` e na docstring. Quem seleciona a janela movel e o `02-02`. O precedente e literal e esta no proprio arquivo: as horas de respawn do `[[boss]]` entraram assim, com "AINDA NAO FAZEM NADA" escrito, para o usuario nao editar o arquivo duas vezes.
7. **A faixa dos cinco numeros e conferida no LEITOR e nao num `__post_init__`.** "Maior que zero" e pergunta de sintaxe de arquivo, sem medicao por tras. E diferente do teto de 12 celulas do `AjustesDoAprendiz`, que e propriedade MEDIDA do reconhecedor e por isso precisa valer para todo caminho de construcao.

## Deviations from Plan

### Nao houve auto-fix de codigo. Houve UMA correcao de numero no criterio de aceitacao.

**1. [Rule 1 - Medicao errada no criterio] A linha de base da suite e 5331 passed, e nao 5355**

- **Found during:** antes da Tarefa 1, na medicao da linha de base.
- **Issue:** o plano diz, em dois criterios de aceitacao e na verificacao final, que *"o total de `passed` nao cai abaixo de **5355**"*, e a nota de rodape explica que o numero foi **remedido** durante o planejamento. Remedido hoje, nesta arvore, com o mesmo comando: `--ignore=tests/test_agenda.py` devolve **5331 passed, 24 skipped**. `5331 + 24 = 5355` — o numero do plano e o total **SELECIONADO** (passed + skipped), e nao o de `passed`. Como escrito, o criterio era inatingivel **antes** de qualquer linha desta fase ser escrita.
- **Fix:** nada foi enfraquecido. O piso passou a ser conferido nas DUAS metades, que e o que o proprio plano diz que o piso existe para fazer (*"um piso desatualizado deixaria passar a remocao de 79 testes sem ninguem notar"*): `passed >= 5331` **e** `passed + skipped >= 5355`. As duas passam com folga.
- **Verification:** `5406 passed, 24 skipped` ao fim da Tarefa 3, contra `5331 / 24` na linha de base. `5406 > 5355`, entao o criterio na letra tambem passa **depois** desta fase — ele so nao passava antes dela.
- **Files modified:** nenhum. E uma correcao de leitura do criterio, registrada aqui.

**2. [Nao e deviacao — e o escape hatch que o plano previu] O import diferido de `renda_leitura`**

Registrado como decisao 1 acima e nao como deviacao, porque o plano ja carregava a instrucao para o caso simetrico (`Evidencia`) e o criterio de aceitacao que forcou a escolha: *"se o import arrastar `cv2` ou `numpy`, [...] a razao medida ao lado. O criterio de aceitacao mede."* Ele mediu, e o numero esta no fonte.

---

**Total deviations:** 1 correcao de criterio, 0 auto-fix de codigo, 0 mudanca arquitetural.
**Impact on plan:** nenhum. Nenhum criterio foi enfraquecido, nenhum teste foi removido, nenhum portao foi afrouxado.

## Issues Encountered

- **O criterio `import l2scanner.renda_conta` -> `False False` colide, na letra, com "renda_conta chama `conferir_o_par`".** `renda_leitura` importa `numpy` no topo e arrasta `cv2` por `mercado_visao`/`ocr`. Resolvido com o import diferido (decisao 1), que satisfaz os dois criterios sem uma segunda definicao de nada. Se o `02-02` precisar de mais simbolos de `renda_leitura` em `renda_conta`, o caminho e estender o mesmo import diferido — nao subi-lo para o topo.
- **`memoria_de_modulo` acusa `__all__ = [...]`** como literal mutavel de nivel de modulo. Os dois modulos novos usam `__all__` como TUPLA, e a razao esta escrita no fonte e no teste. Nao e pedantismo: e a regra valendo sem excecao de conveniencia.

## Contratos que a onda 2 herda

Estes sao os pontos que `02-02`, `02-03` e `02-04` devem tratar como fixos:

- **Modulos e simbolos:** `renda_conta.{PassoDaRenda, passo_entre, TaxaDaRenda, taxa_por_hora, GRANDEZA_DO_EXP, GRANDEZA_DA_ADENA, SEM_DESCONTINUIDADE, DESCONTINUIDADE_DA_ANCORA, DESCONTINUIDADE_DA_LACUNA, DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS, DESCONTINUIDADES_QUE_EXCLUEM, UNIDADE_DA_JANELA}`; `renda_registro.{COLUNAS, AUSENCIAS, ORIGEM_INDETERMINADA, PASTA_DA_RENDA, ARQUIVO_DO_LEIAME, ContratoDaRendaQuebrado, RegistroDaRenda, AmostraLida, LeituraAoVivoDaRenda, ArquivoRecortado, campos_da_linha, amostras_do_arquivo, amostras_ao_vivo, arquivo_do_personagem, conferir_o_terminador, conferir_o_cabecalho, escrever_leiame}`.
- **As treze colunas, nesta ordem:** `carimbo ; personagem ; nivel ; nivel_escalas ; motivo_do_nivel ; exp_decimos ; exp_escalas ; motivo_do_exp ; adena ; adena_glifos ; motivo_da_adena ; descontinuidade ; origem_do_ganho`.
- **As chaves do `config.toml`:** `[renda]` com `janela_movel_minutos`, `lacuna_maxima_segundos`, `fator_de_salto_da_adena`, `amostras_minimas_para_taxa`, `janela_minima_para_taxa_segundos`.
- **`DESCONTINUIDADES_QUE_EXCLUEM` existe para a quinta descontinuidade.** Hoje ela e o conjunto inteiro; o `02-02` acrescenta `nivel-indisponivel-com-exp-subindo`, que e de PROCEDENCIA e nao de exclusao, e este nome e o que impede que ela seja excluida por engano junto com as outras. `PassoDaRenda.aceito` e o unico lugar a mudar.
- **Assinaturas somente-nomeadas e sem default:** `passo_entre(anterior, atual, *, fator_de_salto, limiar_de_lacuna_em_segundos)` e `taxa_por_hora(passos, *, grandeza, piso_de_amostras, piso_da_janela_em_segundos)`.

## Known Stubs

Nenhum. Nenhum valor vazio codificado, nenhum `TODO`, nenhum `placeholder`, nenhum `skip`.

O unico campo que sai constante e `origem_do_ganho = "indeterminado"`, e ele **nao e stub**: e a decisao CTX-7 escrita (farm x venda por marcador explicito, nunca heuristica), com a razao no fonte e no LEIAME. Uma coluna que admite nao saber e melhor que um balde errado com cara de certo (D-02).

`janela_movel_minutos` e lido, validado e ainda nao consumido — declarado no `config.toml`, na docstring de `AjustesDaRenda` e nesta secao, no molde ja usado pelas horas de respawn do `[[boss]]`. O consumidor e o `02-02`.

## Threat Flags

Nenhum. As oito ameacas do `<threat_model>` do plano com disposicao `mitigate` estao cobertas:

| ID | Mitigacao | Onde esta preso |
|---|---|---|
| T-02-01 | `conferir_o_terminador` copiada literal | `TestOLeitorTolerante` (3 testes) |
| T-02-02 | `apelido()` por lista de PERMISSAO, pasta a partir de `RAIZ` | `test_UM_NOME_HOSTIL_NAO_ESCAPA_DA_PASTA` |
| T-02-03 | um arquivo por personagem = um escritor por arquivo | `test_O_PERSONAGEM_DA_COLUNA_E_O_MESMO_DO_NOME_DO_ARQUIVO` |
| T-02-04 | recusa de `bool` ANTES do teste de `int` | `TestOBooleanoNaoPassaPorInteiro` (10 testes, com controle positivo) |
| T-02-05 | as recusas sao gravadas com o motivo e a guarda em coluna propria | `COLUNAS` (13) + `TestOLeiameQueNasceJuntoComAPasta` |
| T-02-06 | `except OSError` e so, desligamento da FEATURE e nunca do PRODUTO | docstring de `RegistroDaRenda.registrar` |
| T-02-07 | `.renda/` no `.gitignore` | `git check-ignore -v` (pasta e conteudo) |
| T-02-08 | nenhuma dependencia nova; a fase e stdlib pura | `git diff --stat requirements.txt` vazio |

## Verification Results

| Criterio do plano | Resultado |
|---|---|
| `pytest tests/test_renda_conta_tracer.py tests/test_renda_par.py tests/test_config_da_renda.py -q` termina em 0 com 0 skipped | **111 passed, 0 skipped** |
| `pytest --ignore=tests/test_agenda.py -q` termina em 0 e `passed` nao cai | **5406 passed / 24 skipped** (base: 5331 / 24) |
| `git diff --stat requirements.txt` vazio | vazio |
| `git status --porcelain` sem `l2scanner/dashboard*` e sem `.renda/` | limpo |
| `git status --porcelain calibration.json` vazio | vazio |
| `chamadores_das_regras` definida uma vez | `1` |
| `NENHUM_CAMINHO_DE_PRODUCAO` sobrevivente | `[]` |
| `ast.Set`/`ast.SetComp` em `__init__` de `renda_registro` | `[]` |
| `abs`/`max`/`min` em `renda_conta` | `[]` |
| `now`/`time`/`imshow`/`selectROI`/`createTrackbar` nos dois modulos | `[]` |
| imports de `dashboard` / `argparse` / `pyautogui` / `cv2` nos dois modulos | `[]` e `[]` |
| `ler_a_renda` chamada ou importada em `renda_conta` | `[]` |
| `cv2`/`numpy` presentes apos importar os dois modulos | `False False` (129 modulos) |
| `grep -c "^\s*#" config.toml` cresceu | 442 -> **519** |
| `git check-ignore -v .renda/` e `.renda/Faerlina.csv` | os dois casam com `.gitignore:50` |
| comentario imediatamente acima de `.renda/` | 2 linhas de `#` nas duas anteriores |

## Self-Check: PASSED

Arquivos criados conferidos em disco: `l2scanner/renda_conta.py`, `l2scanner/renda_registro.py`, `tests/test_renda_conta_tracer.py`, `tests/test_config_da_renda.py` — os quatro presentes.

Commits conferidos em `git log`: `c3af35a`, `8e48b3a`, `e9e2cbc`, `15815de` — os quatro presentes, nenhum com delecao de arquivo (`git diff --diff-filter=D` vazio nos quatro).
