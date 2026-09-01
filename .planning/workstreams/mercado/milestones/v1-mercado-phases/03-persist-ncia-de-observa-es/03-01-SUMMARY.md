---
phase: 03-persist-ncia-de-observa-es
plan: 01
subsystem: database
tags: [csv, stdlib, persistencia, dedup, contrato-de-arquivo, append, windows]

requires:
  - phase: 02-leitura-de-p-gina
    provides: "`LinhaLida` de sete campos (`mercado_leitura.py`) e `PASTA_DO_MERCADO`/`SEPARADOR`/`Catalogo` (`mercado_catalogo.py`)"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "`Relogio.agora()` ancorado, e a doutrina do `Gravador` de degradar a feature e nunca o produto"
provides:
  - "`l2scanner/mercado_registro.py`: a metade PURA (chave de dedup, campos de CSV, o caminho de volta) e a metade de DISCO (`RegistroDeObservacoes`) do registro de observacoes"
  - "`ARQUIVO_DE_OBSERVACOES` e `COLUNAS` — o contrato em disco de `.mercado/observacoes.csv`, seis colunas, ordem travada"
  - "`ContratoDoArquivoQuebrado` — a excecao que a montagem do 03-02 usa para desligar a feature alto"
  - "O portao de contrato de arranque com as DUAS conferencias: terminador de arquivo (D-17) e cabecalho (D-11/D-12)"
  - "Dedup por chave de conteudo com indice em memoria reconstruido do proprio CSV (PERS-02)"
  - "`registrar` que nunca levanta: `OSError` desliga a feature, sai em dois `log.error` e devolve `False` (PERS-03)"
affects: [03-02-montagem, 03-03-portao-humano, fase-4-modo-mercado, DETC-02]

actuals:
  tokens: 19436
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Portao de contrato de arranque: recusar o arquivo INTEIRO sem alterar byte nenhum dele"
    - "Duas familias de falha com niveis distintos: `warning` derruba a linha, `error` desliga a feature"
    - "Append com `flush` e alca aberta/fechada POR LINHA, sem `fsync` e sem reescrita atomica"
    - "Conferencia estrutural por AST no proprio teste (largura de `except`, ausencia de chamadas proibidas)"

key-files:
  created:
    - l2scanner/mercado_registro.py
    - tests/test_mercado_registro.py
  modified: []

key-decisions:
  - "D-17 virou codigo: arquivo que nao termina em quebra de linha e CONTRATO QUEBRADO — a feature desliga alto, nada e lido, e nenhum byte do arquivo do usuario e tocado. As duas saidas alternativas (truncar a cauda; completa-la com `\\n`) estao refutadas por escrito no fonte e presas por AST"
  - "`COLUNAS` travado em seis, na ordem do catalogo irmao: chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos, quantidade, residuo_do_cruzamento. A unidade vive no NOME da coluna; nao ha coluna derivada"
  - "`residuo_dos_campos` ACRESCENTADA ao trio puro do plano: o D-01 exige que `None` e `0` sobrevivam a ida E A VOLTA, e uma volta que morasse no teste seria o teste provando a si mesmo"
  - "O criterio 'cv2 e numpy ausentes de sys.modules' FOI REFUTADO POR MEDICAO e substituido por um que mede a mesma coisa: o registro acrescenta EXATAMENTE UM modulo ao processo alem do que `mercado_catalogo` ja carregava"
  - "`except OSError` e so — nunca `except Exception`, que e o do analog `Gravador` e e largo demais para os quatro modos que a pesquisa mediu"

patterns-established:
  - "Portao de contrato antes das redes por linha: o que o programa nao consegue AFIRMAR sobre o arquivo inteiro e recusado antes de qualquer linha ser lida"
  - "Recusa que nao repara: o caminho de LEITURA nunca escreve sobre dado existente, e a unica escrita do arranque e o cabecalho num arquivo ausente ou de zero bytes"
  - "Aviso de recusa com quatro partes obrigatorias: o que quebrou, as hipoteses POR EXTENSO, o conteudo cru em `%r`, e o que fazer para religar"
  - "Numero que caiu diz que caiu: a medicao que derruba um criterio do plano vira teste que a prende"

requirements-completed: [PERS-01, PERS-02, PERS-03]

coverage:
  - id: D1
    description: "Uma `LinhaLida` atravessa a pilha inteira — chave pura, campos puros, append em disco, releitura de arranque, indice em memoria, dedup — e a segunda tentativa nao aumenta a contagem de linhas"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestUmaObservacaoAtravessaInteira"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestUmaObservacaoAtravessaInteira::test_uma_SESSAO_NOVA_reconstroi_o_indice_do_disco"
        status: pass
    human_judgment: false
  - id: D2
    description: "O contrato de colunas: seis, na ordem travada, com a unidade no nome, sem unitario derivado e sem proveniencia de bancada; e o `;` e a pasta importados do catalogo em vez de redefinidos"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOContratoDasColunas"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOResiduoQueNaoColapsa"
        status: pass
    human_judgment: false
  - id: D3
    description: "O portao do terminador (D-17): os cinco cortes byte a byte medidos sao recusados, o conteudo cru sai no log com as duas hipoteses, e nenhum byte do arquivo do usuario e alterado"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOPortaoDoTerminador"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestALeituraNAO_ESCREVE::test_o_modulo_nao_chama_truncate_em_lugar_nenhum"
        status: pass
    human_judgment: false
  - id: D4
    description: "O cabecalho como contrato com os tres estados distintos, e as duas redes por linha que descartam so a linha ruim do meio sem condenar o arquivo"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOCabecalhoEContrato"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAsDuasRedesPorLinha"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAChaveRepetidaComNomeDiferente"
        status: pass
    human_judgment: false
  - id: D5
    description: "Uma falha de disco desliga a feature de mercado, sai alta no log com a frase que diz o que continua funcionando, devolve `False` e nunca levanta — e o indice nao guarda a chave da linha que nao chegou ao arquivo"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestUmaFalhaDeDiscoDESLIGA_A_FEATURE_E_NAO_O_PRODUTO"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAsCapturasSaoESTREITAS"
        status: pass
    human_judgment: false
  - id: D6
    description: "PERS-03 de ponta a ponta, com o scanner rodando e o mercado ligado — o aviso alto no console e o produto subindo normal"
    verification: []
    human_judgment: true
    rationale: "Nesta fase o mercado NAO TEM CHAMADOR no scanner (declarado no plano, § suposicoes_da_sonda): 'nao derruba os alertas' e verdadeiro por AUSENCIA DE ACOPLAMENTO, nao por um teste de ponta a ponta. O portao de ponta a ponta e da Fase 4 (DETC-02); o 03-03 confere o que da para conferir hoje."

duration: 18min
completed: 2026-08-31
status: complete
---

# Phase 03 Plan 01: Registro de observacoes Summary

**`.mercado/observacoes.csv` ganhou dono unico: append com `flush` e alca por linha, dedup por chave de conteudo reconstruida do disco no arranque, e um portao de contrato que recusa o arquivo inteiro — sem tocar um byte dele — quando ele nao termina em quebra de linha.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-31T03:33:31Z
- **Completed:** 2026-08-31T03:51:37Z
- **Tasks:** 3 (todas TDD: RED -> GREEN)
- **Files created:** 2

## Accomplishments

- **O portao de contrato do D-17 existe e esta medido.** Os cinco cortes byte a byte da pesquisa (36, 35, 34, 33 e 31 bytes) sao recusados 5 de 5, incluindo os DOIS que a contagem de campos aprovaria — e o teste desses dois AFIRMA que eles tem seis campos, para que o proximo leitor veja por que a contagem nao pode ser a primeira rede.
- **Nenhum byte do arquivo do usuario e alterado no caminho de leitura.** A prova e dupla: comportamental (`read_bytes()` antes == depois, em cada um dos cinco cortes e nas recusas por cabecalho) e estrutural (AST: `truncate` nao e chamado em lugar nenhum). As duas saidas recusadas — truncar a cauda, completa-la com `\n` — estao refutadas por escrito no fonte, no molde da casa de nao apagar o que caiu.
- **A dedup fecha a borda que o usuario aceitou de olhos abertos.** O teste da segunda gravacao carrega, em comentario, a entrada 33 do `WINDOWS.md`: numa captura travada UMA pagina e aceita antes do congelamento disparar, e esta dedup e o que impede aquela pagina de virar linha duplicada.
- **`registrar` nunca levanta.** `except OSError` e so, `ligado = False` definitivo para a sessao, duas mensagens `log.error` — a segunda no molde literal de `montar_gravador`, dizendo que morte, saida e ressurreicao seguem sendo detectadas e entregues — e a chave da linha que NAO chegou ao arquivo nao entra no indice.
- **Zero dependencia nova.** `csv`, `io`, `logging`, `datetime`, `pathlib` — tudo stdlib. `tests/test_firewall_escopo.py` continua verde.

## Task Commits

1. **Task 1 (tracer, TDD): o tracer da observacao** — `c4a6172` (test, RED) -> `7dbd885` (feat, GREEN)
2. **Task 2 (TDD): o portao de contrato e as duas redes por linha** — `0287d0e` (test, RED) -> `46a4751` (feat, GREEN)
3. **Task 3 (TDD): a escrita que nunca levanta** — `af3c950` (test, RED) -> `b26301f` (feat, GREEN)

Nenhum passo de REFACTOR foi necessario: as tres implementacoes nasceram na forma final e nao houve limpeza a fazer sobre codigo ja verde.

## Files Created/Modified

- `l2scanner/mercado_registro.py` (NOVO) — as duas metades. Pura: `chave_da_observacao`, `campos_da_observacao`, `chave_dos_campos`, `residuo_dos_campos`. Disco: `RegistroDeObservacoes` com `carregar()`, `_conferir_o_terminador`, `_conferir_o_cabecalho`, `_montar_o_indice`, `_criar_com_cabecalho`, `registrar()`. Mais `ContratoDoArquivoQuebrado`, `ARQUIVO_DE_OBSERVACOES` e `COLUNAS`.
- `tests/test_mercado_registro.py` (NOVO) — 95 testes sobre `tmp_path`, com os cinco cortes medidos, os quatro conteudos hostis e os dois modos de falha reprodutiveis no Windows.

**Nao tocados, de proposito:** `l2scanner/rastreador.py`, `l2scanner/visao.py`, `l2scanner/__main__.py`, e tudo de tiat/bosses/agenda. `git diff --name-only` sobre os seis commits lista exatamente os dois arquivos acima.

## Decisions Made

### 1. A ORDEM das colunas foi travada, e ela e reversibilidade cara

`COLUNAS` vira contrato no disco do usuario no instante em que o primeiro arquivo e criado. A escolha — `chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos, quantidade, residuo_do_cruzamento` — espelha a do catalogo irmao na mesma pasta para que dois arquivos vizinhos nao tenham convencoes diferentes, e carrega a unidade no proprio nome (`total_em_centesimos`) para que `6200` fique autoexplicativo sem coluna derivada. As tres ausencias (unitario, gravacao/frame, `indice`/`serie_nova`) estao escritas no fonte com o motivo de cada uma.

### 2. `residuo_dos_campos` foi acrescentada ao trio puro do plano

O plano especifica tres funcoes puras. Ficaram quatro. O motivo: o D-01 exige que `None` ("nao mediu") e `0` ("conferi e bateu") nao colapsem **na ida E na volta**, e `chave_dos_campos` — cuja assinatura o plano trava como `tuple[str, int, int]` — nao tem por onde devolver o residuo. A alternativa era o teste reimplementar `"" -> None` por conta propria, que seria o teste provando a si mesmo em vez de provar o modulo. A funcao e de quatro linhas e a docstring diz por que ela existe separada.

### 3. `except OSError` e nao `except Exception`

O analog (`gravador.py:190`) usa `except Exception`. Aqui nao, e a razao esta medida: os quatro modos de falha desta maquina — `PermissionError` (13) para arquivo somente-leitura e para nome ocupado por diretorio, `FileNotFoundError` (2) para pasta inexistente, `FileExistsError` (17/winerror 183) para `mkdir` sobre nome de arquivo — sao todos subclasses de `OSError`. Um `except Exception` esconderia um `AttributeError` de refactor futuro como se fosse disco cheio. A largura esta presa por AST no teste.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `Path.read_text()` nao aceita `newline=` no Python 3.12**

- **Found during:** Task 1 (GREEN), no helper `_campos_da_primeira_observacao`
- **Issue:** `TypeError: Path.read_text() got an unexpected keyword argument 'newline'` — o parametro so existe a partir do 3.13, e esta maquina roda 3.12.10. Seis testes quebraram.
- **Fix:** o helper passou a usar `Path.open("r", encoding="utf-8", newline="")` com o `csv.reader` diretamente sobre a alca. Mais fiel ao que o modulo faz, alias.
- **Files modified:** `tests/test_mercado_registro.py`
- **Verification:** os seis testes passaram; os quatro conteudos hostis (inclusive o que contem `\n`) voltam identicos.
- **Committed in:** `7dbd885`

### Um numero que caiu

**2. [Rule 1 - Criterio refutado por medicao] O criterio "modulo leve" e IMPOSSIVEL como escrito, e nao por culpa deste modulo**

- **Found during:** Task 1, ao rodar os criterios de aceitacao
- **Criterio do plano:** `python -c "import sys; import l2scanner.mercado_registro; assert 'cv2' not in sys.modules and 'numpy' not in sys.modules"`
- **Medido:** `import l2scanner.mercado_catalogo` **SOZINHO** ja deixa `cv2` e `numpy` em `sys.modules`, porque ele importa `.config`, que importa `.agenda`/`.cliente`/`.visao`, e `visao` traz os dois. Como importar `PASTA_DO_MERCADO` e `SEPARADOR` do catalogo (em vez de redefinir) e must-have e `key_link` desta mesma fase, as duas exigencias se contradiziam. O must-have venceu.
- **Substituido por** a forma que mede a mesma intencao e da para afirmar: importar `mercado_registro` acrescenta **exatamente um** modulo ao processo alem do que `mercado_catalogo` ja carregava — ele mesmo — e `l2scanner.mercado_leitura` continua **fora** de `sys.modules`, que e o que o `TYPE_CHECKING` compra de verdade.
- **Presos por:** `TestOModuloNaoArrastaAMetadeDeVisao`, com tres testes em subprocesso. O terceiro prende a propria medicao que derrubou o criterio: se um dia alguem aliviar a cadeia de `config` e ele ficar vermelho, e boa noticia e a hora de cobrar de volta a forma forte.
- **Committed in:** `7dbd885`

---

**Total deviations:** 2 (1 bug de compatibilidade de versao, 1 criterio de aceitacao refutado por medicao)
**Impact on plan:** nenhum sobre o escopo. O bug do `read_text` e ambiental. O criterio refutado nao afrouxou nada: a intencao ("o modulo nao arrasta a metade de visao") esta provada de forma mais estreita do que a original teria provado, porque o teste substituto afirma um numero exato em vez de uma ausencia que o analog ja tornava impossivel.

## Issues Encountered

**Os numeros de baseline do plano nao batem com esta arvore, e a diferenca nao e regressao.**

O plano cita baseline `2605 passed, 2 skipped` (sem `test_agenda.py`) e `144 passed` (so ele). Medido nesta arvore, no commit-base `0820587`, **com o arquivo de teste novo excluido**: `2659 passed, 23 skipped` e `145 passed`. A baseline do plano foi medida noutro ponto da historia. O que importa e o invariante que o proprio plano nomeia — *"nenhum teste que passava antes passe a falhar"* — e ele vale: **zero falhas**, e a diferenca de 2754 para 2659 e exatamente os 95 testes novos deste plano.

**O flake conhecido do `test_agenda.py:1141` nao apareceu** nesta rodada: 145 passed, sessao completa, sem aborto.

## User Setup Required

Nenhum. Zero dependencia nova, zero segredo, zero configuracao. `.mercado/observacoes.csv` nasce sozinho no primeiro arranque e ja esta coberto pelo `.gitignore:38`, que e um ignore de DIRETORIO e cobre o conteudo recursivamente.

## Next Phase Readiness

**Pronto para o 03-02 (wave 2):** `RegistroDeObservacoes` e `ContratoDoArquivoQuebrado` estao no lugar com a forma que a funcao de montagem espera. O construtor **nao se defende** de proposito — `mkdir` pode levantar `FileExistsError` (errno 17, medido) e `carregar()` pode levantar `ContratoDoArquivoQuebrado` ou `OSError`. Quem envolve tudo num `try` e `montar_registro_de_mercado`, pelo trilho de `montar_gravador`. Isso esta escrito na docstring da classe para nao se perder.

**Sem consumidor de producao, e isso e desenho.** `LeitorDePagina` nao tem instanciador em `l2scanner/` e o modo `--mercado` e DETC-02, Fase 4. Nada foi ligado no laco, e ligar seria fazer o trabalho da Fase 4.

**Aberto para o 03-03 (portao humano):** T-03-08 (injecao de formula em planilha por nome comecando em `=`/`+`/`-`/`@`) esta deliberadamente **nao mitigado** — prefixar apostrofo sujaria o dado que o criterio 1 manda ser legivel. O `+6 Agathion Alpha Hunter Sealed` existe no fixture versionado, com 15 nomes assim. Item explicito do portao humano.

**Custo aceito do D-17, e ele e real:** uma queda de energia de verdade desliga o registro ate intervencao manual. A mensagem diz ao usuario exatamente o que fazer para religar, e a alternativa era preco errado gravado como bom.

## Self-Check: PASSED

**Arquivos afirmados, conferidos em disco:**
- `l2scanner/mercado_registro.py` — FOUND (30.088 bytes)
- `tests/test_mercado_registro.py` — FOUND (47.656 bytes)
- `.planning/workstreams/mercado/phases/03-persist-ncia-de-observa-es/03-01-SUMMARY.md` — FOUND

**Commits afirmados, conferidos no `git log`:** `c4a6172`, `7dbd885`, `0287d0e`, `46a4751`, `af3c950`, `b26301f` — os seis presentes, na ordem RED/GREEN de cada task.

**Suite:** `tests/test_mercado_registro.py` 95 passed. Fora `test_agenda.py`: 2754 passed, 23 skipped (2659 pre-existentes + 95 novos, zero falhas). `test_agenda.py`: 145 passed, sem o flake.

**Escopo:** `git diff --name-only` sobre os seis commits lista exatamente `l2scanner/mercado_registro.py` e `tests/test_mercado_registro.py`. `rastreador.py`, `visao.py`, `__main__.py` e tudo de tiat/bosses/agenda intocados.

**Nenhum stub:** varredura por `TODO`/`FIXME`/`placeholder`/valores vazios cabeados nao encontrou nada nos dois arquivos. Nao ha secao `Known Stubs`.

---
*Phase: 03-persist-ncia-de-observa-es*
*Completed: 2026-08-31*
