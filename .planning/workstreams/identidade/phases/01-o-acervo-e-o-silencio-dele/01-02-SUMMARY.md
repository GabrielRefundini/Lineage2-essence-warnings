---
phase: 01-o-acervo-e-o-silencio-dele
workstream: identidade
plan: 02
subsystem: identity
tags: [deduplicacao, sha256, ast-gate, calibrar, regressao-de-campo, opencv]

requires:
  - "01-01: l2scanner/acervo.py, chave_da_assinatura, carregar_identidades, Assinatura.anonima"
provides:
  - "carregar_identidades com as duas regras de deduplicacao (chave de conteudo e nome)"
  - "tests/test_calibrar_nao_apaga_identidades.py — a rodada REAL de calibrar.main() com o acervo cheio"
  - "O portao que prende a fusao em memoria DENTRO da memoria (T-01-08)"
  - "A resposta escrita para 'a calibracao e o acervo carregando a mesma pessoa', com o numero"
affects:
  - "Fase 2 (aprender): APRE-04 e o que mantem o residuo anonimo inalcancavel pelo caminho normal"
  - "Fase 3 (batizar): batizar uma entrada do acervo com um nome ja calibrado passa a descarta-la na fusao seguinte"

actuals:
  tokens: 10289   # chars/4 sobre o diff realizado (41155 chars, 45920d7..0c2cf1a)
  tasks: 2
  commits: 3

tech-stack:
  added: []   # zero dependencia nova: ast, json, dataclasses e pathlib sao stdlib
  patterns:
    - "Portao de sobreposicao: interseccao vazia entre 'quem grava' e 'quem conhece', em vez de igualdade que envelhece com a fase"
    - "Numero de bits virados escolhido por MEDICAO tabelada, e nao no olho"
    - "Deteccao por AST tambem para chamadas de metodo, e nao so para imports"

key-files:
  created:
    - "tests/test_calibrar_nao_apaga_identidades.py"
  modified:
    - "l2scanner/acervo.py"
    - "tests/test_acervo.py"

key-decisions:
  - "As regras de deduplicacao sao DUAS e so duas: chave de conteudo e nome nao vazio. Nenhum limiar novo, nenhuma comparacao de pixels — a chave E a comparacao (D-01)"
  - "A precedencia da calibracao continua ESTRUTURAL (ordem da lista + desempate de identificar_linhas), e nao uma condicao paralela"
  - "O residuo anonimo quase-duplicado degrada para SILENCIO, aceito e escrito na docstring com os dois motivos"
  - "O portao de T-01-08 usa INTERSECCAO VAZIA entre 'quem grava' e 'quem conhece o acervo', porque essa forma sobrevive a Fase 2; a igualdade de conjuntos ficou so no lado 'quem grava'"
  - "Deteccao por AST (ast.Call sobre ast.Attribute) em vez de texto sem comentarios, seguindo a licao registrada no 01-01"

patterns-established:
  - "Guarda contra prova vazia em DOIS lados: a rodada aconteceu (o calibration.json mudou) e o detector funciona (caso plantado)"
  - "Premissas do caso medidas ANTES do desfecho: chaves diferentes e as duas pontuacoes acima do limiar, antes de afirmar o silencio"

requirements-completed: [DURA-01, OPER-02]

coverage:
  - id: D8
    description: "Com 4 entradas no acervo, uma rodada COMPLETA de calibrar.main() com --auto --nomes termina 0 e todas continuam no disco byte a byte, enquanto cal.nomes e cal.assinaturas sao reescritos"
    requirement: DURA-01
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestUmaRodadaDeVerdadeNaoEncostaNoAcervo::test_auto_com_nomes_deixa_o_acervo_byte_a_byte_igual"
        status: pass
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestUmaRodadaDeVerdadeNaoEncostaNoAcervo::test_selecionar_passa_pelo_mesmo_portao"
        status: pass
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestUmaRodadaDeVerdadeNaoEncostaNoAcervo::test_com_o_calibration_json_JA_no_disco_o_acervo_continua_intocado"
        status: pass
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestUmaRodadaDeVerdadeNaoEncostaNoAcervo::test_o_acervo_inexistente_nao_quebra_a_rodada_e_nao_e_criado"
        status: pass
    human_judgment: false
  - id: D9
    description: "A garantia e ESTRUTURAL: nenhum campo de Calibracao e do acervo, e quem grava a calibracao nao conhece o acervo (T-01-03)"
    requirement: DURA-01
    verification:
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestAGarantiaEEstrutural::test_nenhum_campo_da_calibracao_e_do_acervo"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestAGarantiaEEstrutural::test_quem_grava_a_calibracao_nao_conhece_o_acervo"
        status: pass
    human_judgment: false
  - id: D10
    description: "O laco do scanner nao regrava o calibration.json: so calibrar.py e calibrar_mercado.py chamam salvar; __main__, sessao e visao ficam de fora (T-01-08)"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestOLacoDoScannerNaoRegravaACalibracao::test_so_os_modulos_de_calibracao_chamam_salvar"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestOLacoDoScannerNaoRegravaACalibracao::test_o_laco_esta_do_lado_de_fora"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_identidades.py#TestOLacoDoScannerNaoRegravaACalibracao::test_o_detector_acusa_um_caso_plantado"
        status: pass
    human_judgment: false
  - id: D11
    description: "Com o acervo VAZIO o reconhecimento e o de hoje: os mesmos 4 nomes nas mesmas 4 linhas, e a lista calibrada volta intacta"
    requirement: OPER-02
    verification:
      - kind: integration
        ref: "tests/test_acervo.py#TestOReconhecimentoDeHojeContinuaIgual::test_com_o_acervo_vazio_o_frame_real_entrega_os_mesmos_nomes"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestOReconhecimentoDeHojeContinuaIgual::test_com_o_acervo_vazio_a_lista_calibrada_volta_intacta"
        status: pass
    human_judgment: false
  - id: D12
    description: "A mesma pessoa nos dois lugares produz UM nome numa linha, e nao uma linha muda — por chave de conteudo e por nome (T-01-09, T-01-10)"
    requirement: OPER-02
    verification:
      - kind: integration
        ref: "tests/test_acervo.py#TestAMesmaPessoaNosDoisLugares::test_conteudo_identico_a_entrada_do_acervo_e_descartada"
        status: pass
      - kind: integration
        ref: "tests/test_acervo.py#TestAMesmaPessoaNosDoisLugares::test_mesmo_nome_e_conteudo_diferente_a_entrada_do_acervo_e_descartada"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestAMesmaPessoaNosDoisLugares::test_nenhuma_calibrada_e_descartada_por_regra_nenhuma"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestAMesmaPessoaNosDoisLugares::test_a_string_vazia_nao_reserva_nome_nenhum"
        status: pass
    human_judgment: false
  - id: D13
    description: "O residuo anonimo quase-duplicado degrada para SILENCIO, com as duas premissas medidas antes do desfecho e o nome errado afirmado ausente"
    requirement: OPER-02
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestOResiduoAnonimoDegradaParaSilencio::test_as_duas_premissas_do_caso_sao_medidas_antes_do_desfecho"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestOResiduoAnonimoDegradaParaSilencio::test_a_linha_CALA_e_o_nome_errado_NAO_sai"
        status: pass
      - kind: integration
        ref: "tests/test_acervo.py#TestOResiduoAnonimoDegradaParaSilencio::test_nenhum_evento_sai_em_nome_de_quem_calou"
        status: pass
    human_judgment: false

duration: 24min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 02: O Acervo e o Silencio Dele — Summary

**Uma rodada de verdade do `calibrar.bat`, com quatro entradas no acervo, termina com a pasta byte a byte identica enquanto `cal.nomes` e `cal.assinaturas` sao reescritos como sempre foram; e a mesma pessoa carregada pela calibracao E pelo acervo passa a produzir um nome numa linha em vez de uma linha muda, porque duas assinaturas quase identicas pontuam 1.000 e 0.921 e a margem de 0.079 cai abaixo dos 0.12 que `identificar_linhas` exige.**

## Performance

- **Duration:** ~24 min
- **Base:** `45920d7` (merge do 01-01)
- **Completed:** 2026-08-31
- **Tasks:** 2
- **Commits:** 3 (a Tarefa 2 e um par RED/GREEN)
- **Files modified:** 3 (1 criado, 2 modificados)

## Accomplishments

- **DURA-01 esta preso por EXECUCAO, e nao por leitura.** `tests/test_calibrar_nao_apaga_identidades.py` roda `l2scanner.calibrar.main()` de verdade, com `--auto` e com `--selecionar`, com `--nomes "Korzis,J4guar,Kaus,TioMad"`, sobre a fixture real `party_ordem_original.png`. Quatro entradas semeadas a mao em `.identidades/` (duas com irmao `nome_<hash>`, duas anonimas) continuam la, com os mesmos nomes de arquivo e os mesmos BYTES.
- **A guarda contra prova vazia e metade do arquivo, e ela morde.** Na MESMA rodada o `calibration.json` gravado tem `nomes` com os quatro nomes e `assinaturas` com quatro entradas novas, cada uma com `altura`, `largura` e `bits`. Verificado por mutacao: trocando os offsets de `capturar_tela` de `(1738, 325)` para `(0, 0)`, os quatro casos de sobrevivencia ficam VERMELHOS — porque a pasta continua intacta pelo motivo errado.
- **Um caso a mais que o plano nao pedia, e ele fecha um ramo:** uma rodada com o `calibration.json` JA no disco, para exercitar o ramo em que `fundir_com_a_calibracao_em_disco` de fato carrega e copia campos. Uma rodada sobre disco vazio nunca chega la, e e nesse ramo que um conserto futuro poderia arrastar o acervo para dentro do arquivo.
- **T-01-08 esta preso.** O conjunto de modulos de `l2scanner/` que chamam `salvar` e exatamente `{calibrar.py, calibrar_mercado.py}`, lido da arvore sintatica. `__main__.py`, `sessao.py` e `visao.py` estao nomeadamente fora. Se a fusao em memoria do 01-01 algum dia vazar para o arquivo, D-04 seria desfeito pelo lado de dentro — e as entradas ANONIMAS (`nome: ""`) morreriam junto com `cal.assinaturas` na proxima `calibrar.bat`.
- **OPER-02: a resposta esta escrita, com o numero.** `carregar_identidades` ganhou duas regras e uma docstring que responde as tres perguntas que o codigo nao mostra. Sem elas o desfecho nao seria neutro, seria o PIOR possivel: acrescentar ao acervo alguem que ja estava calibrado o faria PARAR de ser reconhecido.
- **O residuo esta escrito como resposta deliberada, e nao escondido.** Uma entrada anonima parecida com uma calibrada cai no silencio pela margem. Aceito por dois motivos que estao na docstring: e o unico desfecho SEGURO da familia (a linha cala em vez de mentir), e nao e alcancavel pelo caminho normal, porque a Fase 2 so grava depois de nao casar com nada ja gravado (APRE-04).

## Task Commits

1. **Tarefa 1: uma rodada de verdade do `calibrar.bat`, com o acervo cheio** — `b9d605c` (test)
2. **Tarefa 2 (RED): a convivencia entre a calibracao e o acervo** — `676b166` (test)
3. **Tarefa 2 (GREEN): as duas regras de deduplicacao** — `0c2cf1a` (feat)

## Registros exigidos pelo `<output>` do plano

### 1. As pontuacoes medidas no caso do quase-duplicado anonimo

Medido nesta fixture (`tests/fixtures/identidade/party_ordem_original.png`), linha 1
(`J4guar`), mascara `20x100` com 48 pixels de texto. A copia e obtida virando N bits
deterministicos da mascara (`np.random.RandomState(42)`), o que muda a chave `sha256` e
nao muda a imagem o bastante para derrubar a correlacao:

| bits virados | calibrada | copia  | margem | desfecho de `identificar_linhas` |
|--------------|-----------|--------|--------|----------------------------------|
| 1            | 1.0000    | 0.9895 | 0.0105 | SILENCIO                         |
| 2            | 1.0000    | 0.9793 | 0.0207 | SILENCIO                         |
| 3            | 1.0000    | 0.9694 | 0.0306 | SILENCIO                         |
| 5            | 1.0000    | 0.9487 | 0.0513 | SILENCIO                         |
| **8**        | **1.0000**| **0.9212** | **0.0788** | **SILENCIO** (o caso usado nos testes) |
| 12           | 1.0000    | 0.8879 | 0.1121 | SILENCIO (ainda abaixo de 0.12)  |
| 20           | 1.0000    | 0.8306 | 0.1694 | `"J4guar"` (a margem passou)     |
| 40           | 1.0000    | 0.7237 | 0.2763 | `"J4guar"`                       |

**O numero que a Fase 2 precisa:** a faixa perigosa vai de 1 a ~14 bits de diferenca. Ali
as duas pontuacoes ficam bem acima de `LIMIAR_DE_CASAMENTO = 0.75` e a margem fica abaixo
de `MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12`. Acima de ~15 bits o guloso volta a discriminar
e a calibrada ganha a linha. **A previsao do plano ("~1.000 e ~0.98") estava do lado certo
mas otimista sobre a fragilidade: bastam 12 bits virados numa mascara de 2000 celulas para
a linha calar.** Isso e o que torna APRE-04 (a Fase 2 so grava o que nao casou com nada ja
gravado) uma exigencia de correcao, e nao uma otimizacao de espaco.

### 2. Contagem de testes

| Momento | Passaram | Skipped |
|---------|----------|---------|
| Linha de base (`45920d7`, apos o 01-01) | 3104 | 23 |
| Depois da Tarefa 1 | 3116 | 23 |
| Fim do plano | **3130** | 23 |

Delta: **+26** (12 casos em `tests/test_calibrar_nao_apaga_identidades.py`, 14 em
`tests/test_acervo.py`). Nenhum teste existente foi editado, afrouxado ou removido. Os 23
skipped sao os mesmos da linha de base (OCR/WinRT, cujas bindings vivem na `.venv` e nao no
`python` do sistema — esta execucao usou `Python 3.12.10` do sistema, dentro do worktree).

**RED confirmado antes do GREEN:** com os testes da Tarefa 2 no lugar e `carregar_identidades`
ainda em concatenacao pura, `python -m pytest tests/test_acervo.py -q` deu **5 failed, 61
passed**. Os cinco vermelhos eram exatamente os que dependem das regras de deduplicacao.

## Files Created/Modified

- `tests/test_calibrar_nao_apaga_identidades.py` — **criado.** 12 casos. Irmao declarado de `tests/test_calibrar_nao_apaga_mercado.py`, com a docstring dizendo em voz alta o que os separa: o irmao prova PRESERVACAO dentro do mesmo arquivo; este prova que existe um lugar que o caminho de escrita NAO ALCANCA.
- `l2scanner/acervo.py` — `carregar_identidades` ganha as duas regras e a docstring que responde as tres perguntas. A assinatura publica nao muda. Nenhum outro simbolo do modulo foi tocado.
- `tests/test_acervo.py` — 14 casos novos em quatro classes (`TestOReconhecimentoDeHojeContinuaIgual`, `TestAMesmaPessoaNosDoisLugares`, `TestOResiduoAnonimoDegradaParaSilencio`, `TestADocstringRespondeAPergunta`), mais o helper `quase_igual` e a tabela de medicao em comentario. Os 52 casos que ja existiam nao foram tocados.

## Decisions Made

- **As regras sao DUAS, e nenhuma delas e um limiar.** Chave de conteudo e nome nao vazio. O plano proibia inventar um segundo criterio de igualdade dentro do mesmo modulo, e isso foi respeitado: nao ha comparacao de pixels nova, nenhum "parecido o suficiente".
- **O nome precisa ser NAO VAZIO para a regra (b) valer.** Duas entradas anonimas tem o mesmo "nome" — a string vazia. Sem essa condicao, a segunda anonima seria descartada por parecer duplicata da primeira, e o acervo so conseguiria guardar UMA pessoa sem nome no mundo inteiro. Ha um caso dedicado a isso (`test_a_string_vazia_nao_reserva_nome_nenhum`), porque e o modo de falha mais facil de introduzir escrevendo a regra de cabeca.
- **A precedencia continua ESTRUTURAL.** As calibradas entram primeiro na lista e o desempate `max(..., -i, -j)` de `identificar_linhas` faz o resto. Nenhuma condicao "se for calibrada, prefira" foi escrita — ela seria uma segunda regra de precedencia, e duas regras para a mesma coisa divergem na primeira vez que alguem mexer numa sem lembrar da outra.
- **O portao de T-01-08 tem DUAS formas, e cada uma cobre uma coisa.** A igualdade de conjuntos sobre "quem grava uma `Calibracao`" (`{calibrar.py, calibrar_mercado.py}`) e o portao forte, e um escritor novo do `calibration.json` merece olhos humanos. A INTERSECCAO VAZIA entre "quem grava" e "quem conhece o acervo" e a forma que **sobrevive a Fase 2**: la mais modulos vao importar o acervo, e nenhum deles vai gravar o `calibration.json`.
- **O numero de bits virados saiu de uma tabela medida, e nao do olho.** A tabela esta em comentario no proprio teste, para que quem mexer no limiar ou na margem no futuro veja imediatamente onde a faixa perigosa comeca e acaba.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O portao de `salvar` nasceria fragil na forma textual escrita no plano**

- **Found during:** Tarefa 1
- **Issue:** O plano especificava "varre `l2scanner/*.py`, remove linhas de comentario, e monta o conjunto dos modulos cujo texto restante chama `salvar`". Remover linhas de comentario nao remove DOCSTRINGS, e docstring que explica `salvar` e exatamente o tipo de prosa que este projeto escreve. E a mesma armadilha registrada no 01-01, em que um portao textual acusou tres modulos que citavam o acervo em prosa. A `calibracao.py` tambem cairia dentro por definir `def salvar`, sem chamar ninguem.
- **Fix:** A deteccao le a arvore sintatica (`ast.Call` cujo `func` e um `ast.Attribute` com `attr == "salvar"`). A assercao exata que o plano pediu — igualdade de conjuntos, com `__main__.py`, `sessao.py` e `visao.py` fora — foi preservada. Dois casos guardam o detector: um caso plantado que ele TEM de acusar, e um texto so com prosa e comentario que ele NAO pode acusar.
- **Files modified:** `tests/test_calibrar_nao_apaga_identidades.py`
- **Verification:** `python -m pytest tests/test_calibrar_nao_apaga_identidades.py -q` — 12 passed. O conjunto observado e `{calibrar.py, calibrar_mercado.py}`.
- **Committed in:** `b9d605c`

**2. [Rule 2 - Missing Critical] O portao "quem grava nao conhece o acervo", que o plano nao pedia**

- **Found during:** Tarefa 1
- **Issue:** O plano pedia a afirmacao positiva sobre `dataclasses.fields(Calibracao)`. Ela e correta e esta la, mas e fraca sozinha: um campo do acervo e so UMA das formas de o caminho de escrita alcancar a pasta. A outra — e a mais provavel na Fase 2 — e `calibrar.py` passar a IMPORTAR o acervo por qualquer motivo, e ganhar duas linhas depois uma escrita.
- **Fix:** Interseccao vazia entre o conjunto de quem grava uma `Calibracao` e o conjunto de quem importa `acervo`, ambos lidos da arvore. Escolhida a forma de INTERSECCAO em vez de igualdade justamente para que ela nao envelheca com a Fase 2.
- **Files modified:** `tests/test_calibrar_nao_apaga_identidades.py`
- **Verification:** caso `test_quem_grava_a_calibracao_nao_conhece_o_acervo`, verde.
- **Committed in:** `b9d605c`

**3. [Rule 2 - Missing Critical] A rodada que passa pela FUSAO, e nao pelo atalho do arquivo ausente**

- **Found during:** Tarefa 1
- **Issue:** Todos os casos que o plano descrevia rodam sobre `tmp_path` vazio. `fundir_com_a_calibracao_em_disco` devolve `nova` sem ler nada quando o arquivo nao existe, entao NENHUM deles exercitaria o ramo em que a fusao de fato carrega o disco e copia campos por `setattr`. E justamente esse o ramo onde um conserto futuro arrastaria o acervo para dentro do arquivo.
- **Fix:** Um caso a mais que roda `main()` duas vezes: a primeira cria o `calibration.json`, a segunda roda com ele ja no disco e com o acervo semeado entre as duas.
- **Files modified:** `tests/test_calibrar_nao_apaga_identidades.py`
- **Verification:** caso `test_com_o_calibration_json_JA_no_disco_o_acervo_continua_intocado`, verde.
- **Committed in:** `b9d605c`

**4. [Rule 2 - Missing Critical] O caso da string vazia contra a string vazia**

- **Found during:** Tarefa 2
- **Issue:** O plano descreve a regra (b) como "o nome dela nao e vazio e ja aparece entre os nomes calibrados". A condicao "nao e vazio" e facil de esquecer ao escrever a regra, e o efeito de esquece-la e silencioso e desproporcional: `"" in {""}` e verdadeiro, entao a segunda entrada anonima do acervo seria descartada por parecer duplicata da primeira, e o acervo passaria a guardar no maximo UMA pessoa sem nome — matando a Fase 2 inteira sem nenhum erro em lugar nenhum.
- **Fix:** Um caso dedicado com tres anonimas de conteudos diferentes mais uma calibrada, afirmando `conhecidas == 4` e `sem_nome == 3`.
- **Files modified:** `tests/test_acervo.py`
- **Verification:** caso `test_a_string_vazia_nao_reserva_nome_nenhum`, verde; a implementacao usa `if do_acervo.nome and do_acervo.nome in nomes_calibrados`.
- **Committed in:** `676b166` (RED) / `0c2cf1a` (GREEN)

**5. [Rule 1 - Bug] Duas assercoes minhas estavam erradas sobre o contrato existente**

- **Found during:** Tarefa 2 (na primeira rodada RED)
- **Issue:** (a) escrevi `calibracao.nome_da_linha(0) == "Membro 1"`, mas a linha 0 e `Korzis`, que NAO tem assinatura nesse caso — o rotulo por posicao volta a valer e o retorno correto e `"Korzis"`. (b) escrevi `obs.linhas[N].nome == ""` para a linha que cai no silencio, mas `""` significa "casou com uma assinatura anonima" e o silencio produz `None`. As duas eram erro do teste, e nao do codigo.
- **Fix:** (a) passou a afirmar `nome_da_linha(1) == "Membro 2"`, que e a linha do `J4guar` — a que TEM assinatura e portanto nao pode ser emprestada. (b) passou a afirmar `is None`, com o comentario explicando a diferenca entre os dois estados.
- **Files modified:** `tests/test_acervo.py`
- **Verification:** ambos verdes, e nenhum codigo de producao foi alterado para acomoda-los.
- **Committed in:** `676b166`

---

**Total deviations:** 5 auto-fixed (2 bugs, 3 missing critical)
**Impact on plan:** Nenhum escopo novo e nenhuma decisao travada tocada. A deviation 1 troca a TECNICA de um portao preservando a assercao exata que o plano pediu; as deviations 2, 3 e 4 acrescentam casos que atendem criterios que o proprio plano escreveu (a garantia estrutural, a rodada real, a regra do nome nao vazio); a deviation 5 conserta o teste, nunca o codigo.

## Issues Encountered

- **Conflito com os workstreams `discord` e `mercado`: nenhum.** Nada em `l2scanner/ponte_*.py`, `l2scanner/mercado_*.py`, `l2scanner/calibrar_mercado.py`, `tools/medir_*.py` ou nos testes de mercado foi lido para escrita, alterado ou reformatado. `l2scanner/calibrar.py` e `l2scanner/calibracao.py` foram apenas LIDOS.
- **Uma atencao para a proxima leitura:** o caso `test_so_os_modulos_de_calibracao_chamam_salvar` afirma igualdade com `{calibrar.py, calibrar_mercado.py}`. Se o workstream `mercado` acrescentar um modulo novo que grava a `Calibracao`, este caso fica vermelho de proposito, e a mensagem de falha diz exatamente isso — um escritor novo do `calibration.json` precisa de olhos humanos, porque foi um escritor que apagou 13 moldes de glifo em 2026-08-30.

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder nem componente sem fonte de dados neste plano.

O que **deliberadamente nao existe** (e nao e stub, e fronteira de fase ja declarada no 01-01):

- `AcervoDeIdentidades.nomear` — batizar e Fase 3 (D-03).
- Qualquer chamador de `gravar` no laco do scanner — aprender e Fase 2.
- **O residuo anonimo quase-duplicado nao e um stub, e uma resposta.** Ele degrada para silencio, isso esta escrito na docstring de `carregar_identidades` com os dois motivos, e ha tres testes que o afirmam. Consertar isso exigiria um segundo criterio de igualdade dentro do modulo, que o plano proibiu por escrito.

## Threat Flags

Nenhuma superficie nova. As quatro ameacas que este plano mitiga estavam todas no `<threat_model>`:

| Threat ID | Disposicao | Onde ficou provada |
|-----------|-----------|--------------------|
| T-01-03 | mitigada | `TestUmaRodadaDeVerdadeNaoEncostaNoAcervo` + `TestAGarantiaEEstrutural` |
| T-01-08 | mitigada | `TestOLacoDoScannerNaoRegravaACalibracao` + `test_quem_grava_a_calibracao_nao_conhece_o_acervo` |
| T-01-09 | mitigada | `TestAMesmaPessoaNosDoisLugares` + `TestOResiduoAnonimoDegradaParaSilencio` |
| T-01-10 | mitigada | `test_nenhuma_calibrada_e_descartada_por_regra_nenhuma` |

T-01-SC continua valendo: nenhuma dependencia nova foi instalada, e nenhuma tarefa deste plano instala nada. `ast`, `json`, `dataclasses` e `pathlib` sao stdlib.

## User Setup Required

Nenhuma.

## Next Phase Readiness

**Os sete criterios da Fase 1 estao cobertos.** Os criterios 3 a 7 sairam do plano 01-01; os criterios 1 (DURA-01) e 2 (OPER-02) saem deste.

**Pronto para a Fase 2 (aprender assinaturas):**

- `gravar` existe, esta provada e continua sem chamador.
- **A tabela de medicao acima e o insumo direto de APRE-04.** A faixa perigosa (1 a ~14 bits de diferenca entre duas capturas da mesma pessoa) e exatamente o que a Fase 2 precisa NAO produzir. Gravar uma entrada nova sem antes conferir que ela nao casa com nada ja gravado criaria quase-duplicados dentro da faixa, e cada um deles cala uma linha.
- Os dois portoes de fronteira de fase do 01-01 (`test_so_dois_modulos_conhecem_o_acervo` e `test_o_laco_real_nao_encosta_no_acervo`) continuam la e continuam sendo os que a Fase 2 ajusta e apaga DE PROPOSITO. O portao novo deste plano (`test_quem_grava_a_calibracao_nao_conhece_o_acervo`) **nao** e um deles: ele foi escrito na forma que sobrevive a Fase 2.

**Pronto para a Fase 3 (batizar):** batizar uma entrada do acervo com um nome que ja esta calibrado passa a descarta-la na fusao seguinte, pela regra (b). Isso e o comportamento correto — a calibrada vence — mas quem escrever o batismo precisa saber que o efeito visivel e "a entrada some da lista", e nao "nada aconteceu".

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- FOUND `tests/test_calibrar_nao_apaga_identidades.py`
- FOUND `l2scanner/acervo.py`
- FOUND `tests/test_acervo.py`

Commits afirmados, conferidos em `git log`:

- FOUND `b9d605c`
- FOUND `676b166`
- FOUND `0c2cf1a`

Suite conferida por execucao: `python -m pytest tests/ -q` — **3130 passed, 23 skipped** em 75s.

---
*Phase: 01-o-acervo-e-o-silencio-dele*
*Workstream: identidade*
*Completed: 2026-08-31*
