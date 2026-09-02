---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 03
subsystem: persistencia
tags: [decimal, regex, validacao, escrita-atomica, os.replace, fsync, json, tdd]

requires:
  - phase: 01-01
    provides: "l2scanner/dashboard_dados.py com payload puro, cuja pureza este modulo preserva ao NAO ser importado por ele"
provides:
  - "l2scanner/dashboard_cambio.py — MOLDE_DO_CAMBIO, MENSAGEM_DE_CAMBIO_INVALIDO, CambioInvalido, HistoricoDoCambioIlegivel, Cambio, interpretar_o_cambio, gravar_o_cambio, ler_o_cambio"
  - "O portao de duas camadas (forma antes do valor) com controle negativo provando que a primeira camada faz trabalho"
  - "A escrita atomica com pid no temporario e fsync, e a estrutura de lista que so cresce em .mercado/cambio.json"
  - "ARQUIVO_DO_CAMBIO e SUFIXO_TEMPORARIO, para quem for contar temporarios ou nomear o arquivo"
affects: [01-05, 01-06, 01-07]

actuals:
  tokens: 8364
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Portao de duas camadas com a camada externa TESTADA SOZINHA num controle negativo, para a camada interna nao virar enfeite"
    - "Assimetria deliberada leitura/escrita sobre o mesmo arquivo corrompido: leitura degrada para nulo, escrita RECUSA"
    - "Escrita atomica com fsync, divergindo dos tres analogos da arvore, com o motivo e o custo medido escritos ao lado"

key-files:
  created:
    - l2scanner/dashboard_cambio.py
    - tests/test_dashboard_cambio.py
  modified: []

key-decisions:
  - "Espaco EM VOLTA e tolerado por strip(); espaco no MEIO nao. O strip so remove branco e nao consegue transformar nenhuma forma recusada numa aceita"
  - "O valor viaja como STRING no JSON: serializar como numero faria json.load devolver float, reintroduzindo na fronteira do disco o erro que o Decimal existe para tirar"
  - "Gravar sobre um cambio.json ilegivel RECUSA (HistoricoDoCambioIlegivel) em vez de sobrescrever — apagar o historico e a unica acao destrutiva possivel nesta fase"
  - "O valor guardado no arquivo atravessa o MESMO portao do campo do formulario, senao a validacao seria contornavel por um editor de texto"
  - "fsync acrescentado ao molde da casa, com o custo medido (9,18 ms) e o motivo escritos no fonte"

patterns-established:
  - "Controle negativo que chama a camada interna REAL, e nao uma reimplementacao — uma reimplementacao provaria so que ela e permissiva"
  - "Refutacao com medicao no fonte: a linha 'digitos Unicode -> recusado' da pesquisa esta corrigida no comentario do molde, com o valor que Decimal produz"

requirements-completed: [DASH-02]

coverage:
  - id: D1
    description: "Um texto que nao seja um numero positivo em forma decimal simples e RECUSADO no servidor, com a frase travada no UI-SPEC"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_a_tabela_MEDIDA_da_pesquisa_INTEIRA"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_a_excecao_CARREGA_a_mensagem_travada_e_nao_uma_improvisada"
        status: pass
    human_judgment: false
  - id: D2
    description: "As formas que a validacao por valor sozinha aceitaria (1e3, 1_0, +0.5, numero longo demais, digito Unicode) tem teste com nome proprio recusando cada uma"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_notacao_de_EXPOENTE_e_recusada_1e3_valeria_MIL"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_SUBLINHADO_e_recusado_1_0_valeria_DEZ_vinte_vezes_o_pretendido"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_SINAL_explicito_e_recusado_mais_0_ponto_5"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_numero_LONGO_DEMAIS_e_recusado_antes_de_virar_layout"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOPortaoDeDuasCamadas::test_digito_UNICODE_nao_ASCII_e_recusado"
        status: pass
    human_judgment: false
  - id: D3
    description: "O CONTROLE NEGATIVO: a segunda camada, chamada sozinha sobre as mesmas formas, as ACEITA — a prova de que a camada da forma nao e decorativa"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOControleNegativoDaSegundaCamada::test_a_segunda_camada_SOZINHA_ACEITA_o_que_o_molde_recusa"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestOControleNegativoDaSegundaCamada::test_o_molde_SEM_re_ASCII_deixaria_o_digito_arabe_passar"
        status: pass
    human_judgment: false
  - id: D4
    description: "A taxa persiste entre sessoes num arquivo que so cresce; a gravacao e atomica, carimbada e sem lixo"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_gravar_de_novo_APENDA_e_o_PRIMEIRO_continua_no_arquivo"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_duzentas_gravacoes_nao_deixam_UM_temporario_para_tras"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_gravar_sobre_um_destino_que_JA_EXISTE_deixa_o_arquivo_INTEIRO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_cada_registro_carrega_o_valor_e_o_carimbo_em_ISO"
        status: pass
    human_judgment: false
  - id: D5
    description: "Sem taxa informada a leitura devolve nulo e nenhum valor padrao e chutado; um arquivo corrompido nao levanta, avisa e NAO e apagado"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_ler_de_uma_pasta_SEM_o_arquivo_devolve_NULO_e_NAO_cria_o_arquivo"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_JSON_corrompido_devolve_NULO_avisa_e_NAO_apaga_o_arquivo"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_um_valor_ILEGAL_editado_a_MAO_no_arquivo_devolve_NULO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_cambio.py#TestAPersistenciaCarimbada::test_gravar_sobre_um_historico_ILEGIVEL_RECUSA_em_vez_de_APAGAR"
        status: pass
    human_judgment: false
  - id: D6
    description: "A frase de recusa desenhada no rodape da pagina: o campo mantem o texto digitado, o botao volta, e o R$ exibido continua sendo o do cambio ANTIGO"
    verification: []
    human_judgment: true
    rationale: "O que e afirmavel sem navegador — a recusa no servidor, a frase travada, e o arquivo do cambio anterior intocado — esta coberto por D1 e D5. O que sobra e o desenho do estado de erro no formulario, que so existe depois do 01-05 (POST) e do 01-07 (JS), e que o 01-CONTEXT declarou verificacao humana (Playwright recusado por instalador pesado)."

duration: 14min
completed: 2026-09-02
status: complete
---

# Phase 01 Plan 03: O cambio XM -> BRL Summary

**O portao de duas camadas que recusa `1e3`, `1_0`, `+0.5` e o cinco arabe-indico antes de o `Decimal` os transformar em mil, dez, meio e cinco — com controle negativo provando que a camada da forma faz trabalho — mais a persistencia carimbada em `.mercado/cambio.json`, uma lista que so cresce, escrita com `os.replace` e `fsync`.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-09-02T01:46:25Z
- **Completed:** 2026-09-02T01:58:20Z
- **Tasks:** 2 de 2
- **Files modified:** 2 (2 criados, 0 alterados)
- **Suite:** 4.560 passed, 25 skipped (era 4.517 antes do plano; +43 testes, todos deste plano)

## Accomplishments

- **O portao de duas camadas existe, na ordem certa, e a ordem esta escrita.** `MOLDE_DO_CAMBIO` julga a FORMA; so o que sobrevive chega ao `Decimal`, que julga o VALOR. Cada pedaco do molde tem um comentario dizendo o que ele recusa e por que.
- **O controle negativo esta no lugar e chama a camada interna REAL.** `_apenas_o_valor` foi separada em funcao propria por um motivo unico: o teste precisa chama-la SEM o molde na frente. Uma reimplementacao no teste provaria apenas que a reimplementacao e permissiva — que nao e a afirmacao que interessa.
- **Uma linha da tabela da pesquisa foi REFUTADA por medicao, e a correcao mora no fonte.** A pesquisa dava "digitos Unicode -> recusado" pelo `Decimal`. Medido nesta arvore (3.12.10): a recusa vinha do **separador** Unicode (`٠٫٥`, `０．５`), nao do digito. Um digito Unicode **sozinho** — `٥`, `５` — vira `Decimal('5')` sem esforco, **e tambem casa com `\d` num regex sem `re.ASCII`**. Sem a flag, as duas camadas o aceitariam. Ha teste com nome proprio recusando-o e um segundo teste compilando o mesmo padrao **sem** a flag para mostrar que ela e a unica coisa que o pega.
- **A gravacao apenda, e atomica, e nao deixa lixo:** 200 gravacoes seguidas produzem 200 registros e **zero** temporarios remanescentes.
- **Nao ha nenhuma acao destrutiva no modulo.** Nem no caminho normal (a lista so cresce), nem no caminho do arquivo corrompido (leitura degrada, escrita recusa), nem no caminho da recusa (um texto invalido nao encosta no disco — ha teste comparando os bytes do arquivo antes e depois).

## Task Commits

1. **Tarefa 1: O portao de duas camadas — RED** — `4f38989` (test)
2. **Tarefa 1: O portao de duas camadas — GREEN** — `3f960a4` (feat)
3. **Tarefa 2: A persistencia carimbada — RED** — `25225f3` (test)
4. **Tarefa 2: A persistencia carimbada — GREEN** — `4b19472` (feat)

**Plan metadata:** ver o commit `docs(01-03)` deste SUMMARY.

_As duas tarefas sao `tdd="true"` e por isso tem dois commits cada. Nao houve REFACTOR em nenhuma das duas: o codigo saiu do GREEN sem duplicacao a remover._

## TDD Gate Compliance

Os quatro portoes estao no `git log`, na ordem, dois ciclos completos:
`test(01-03)` → `feat(01-03)` → `test(01-03)` → `feat(01-03)`.

O RED de cada ciclo foi executado e **falhou** antes do GREEN correspondente
(`ModuleNotFoundError: No module named 'l2scanner.dashboard_cambio'` no primeiro,
`ImportError: cannot import name 'ARQUIVO_DO_CAMBIO'` no segundo). Nenhum teste
passou inesperadamente na fase RED.

## Files Created/Modified

**Criados**
- `l2scanner/dashboard_cambio.py` — `TETO_DE_DIGITOS_INTEIROS`, `TETO_DE_CASAS_DECIMAIS`, `MOLDE_DO_CAMBIO`, `MENSAGEM_DE_CAMBIO_INVALIDO`, `CambioInvalido`, `_apenas_o_valor`, `interpretar_o_cambio`, `ARQUIVO_DO_CAMBIO`, `SUFIXO_TEMPORARIO`, `CAMPO_DO_VALOR`, `CAMPO_DO_CARIMBO`, `HistoricoDoCambioIlegivel`, `Cambio`, `_escrever`, `_historico`, `gravar_o_cambio`, `ler_o_cambio`
- `tests/test_dashboard_cambio.py` — 43 testes em tres classes: `TestOPortaoDeDuasCamadas`, `TestOControleNegativoDaSegundaCamada`, `TestAPersistenciaCarimbada`

**Alterados:** nenhum. `requirements.txt` nao ganhou uma linha; nenhum arquivo do workstream `mercado` foi tocado.

## Decisions Made

- **Espaco EM VOLTA e tolerado, espaco no MEIO nao.** `Decimal` ja ignora branco nas pontas e `conferir_o_cabecalho` ja faz `strip()` no mesmo espirito. Colar `"0,50 "` de outra janela e um acidente comum e inofensivo, e responder a ele com *"informe um numero maior que zero"* para quem digitou exatamente um numero maior que zero seria a mensagem mentindo. O `strip()` remove **so** branco: ele nao consegue transformar nenhuma das formas recusadas numa aceita. Ha teste prendendo `"0, 50"` como recusado.
- **O valor viaja como STRING no JSON, e a conversao esta declarada no ponto exato.** JSON nao tem `Decimal`. Serializar como numero faria `json.load` devolver `float`, e `0.50` deixaria de ser exatamente `0.50` no caminho de volta — reintroduzindo, na fronteira do disco, o erro de representacao que o `Decimal` existe para tirar.
- **`fsync` acrescentado ao molde da casa, divergindo dos tres analogos.** `calibracao.py`, `loot.py` e `acervo.py` fazem `write_text` + `os.replace` sem sincronizar. Sem `fsync`, o `os.replace` e atomico quanto ao **nome** mas nao quanto aos **bytes**: numa queda de energia logo apos a troca, o diretorio pode apontar para um arquivo cujo conteudo ainda nao desceu do cache. A pesquisa mediu o custo em **9,18 ms** — irrelevante para uma escrita por clique, e este e o unico arquivo que este processo escreve. O motivo e o custo estao no fonte.
- **A estrutura e uma LISTA que so cresce, e o motivo esta escrito.** Custa a mesma linha que um valor unico e compra duas coisas: a resposta a *"qual cambio estava valendo quando"* (T-01-12), e a forma que a coleta automatica pelo listener dos grupos de venda vai preencher quando existir — ela produz uma **serie** de cotacoes carimbadas, nao um valor.
- **Os tetos de digitos (7 inteiros, 4 decimais) sao ESCOLHA, NAO MEDICAO**, e estao rotulados assim no fonte, no molde de `mercado_analise.py:152-176`. Ninguem mediu quanto o XM pode valer; se o mercado enlouquecer, e uma linha.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `HistoricoDoCambioIlegivel`: gravar sobre um `cambio.json` corrompido RECUSA em vez de sobrescrever**
- **Found during:** Tarefa 2 (a persistencia)
- **Issue:** O plano especifica o comportamento da LEITURA sobre um arquivo corrompido (nulo + aviso, sem apagar), mas nao o da ESCRITA. A implementacao obvia — ler o historico existente, tratar falha como lista vazia, gravar — **apagaria em silencio todo o historico de cambios do usuario** na primeira vez que ele salvasse uma taxa depois de o arquivo ter sido corrompido por uma edicao a mao. Isso e exatamente a acao destrutiva que a linha "confirmacao destrutiva" do UI-SPEC afirma nao existir nesta fase, e destroi a unica evidencia que sustenta T-01-12 (qual cambio valia quando).
- **Fix:** `_historico` levanta `HistoricoDoCambioIlegivel` (subclasse de `OSError`) quando o arquivo existe e nao e a lista esperada, e `gravar_o_cambio` propaga. A mensagem segue a anatomia da casa: o que aconteceu, que NENHUM byte foi alterado, o que fazer (consertar ou renomear), e o que continua funcionando (a pagina segue mostrando XM). A **assimetria leitura/escrita e deliberada e esta escrita na docstring**: na leitura, degradar para nulo custa o R$ da tela por uma volta; na escrita, degradar custaria o registro do usuario para sempre.
- **Files modified:** `l2scanner/dashboard_cambio.py`, `tests/test_dashboard_cambio.py`
- **Verification:** `test_gravar_sobre_um_historico_ILEGIVEL_RECUSA_em_vez_de_APAGAR` — afirma que a excecao sobe, que os bytes originais continuam intactos, e que nenhum temporario ficou para tras
- **Committed in:** `25225f3` (RED) e `4b19472` (GREEN)
- **Nota de superficie:** isto acrescenta **um** nome a lista de artefatos do plano. Nenhum outro nome foi acrescentado, e nenhum dos oito nomes previstos falta.

**2. [Rule 2 - Missing Critical] O valor guardado no arquivo atravessa o MESMO portao do campo do formulario**
- **Found during:** Tarefa 2 (a persistencia)
- **Issue:** O plano especifica que JSON corrompido devolve nulo. Mas um `cambio.json` **sintaticamente valido** com `{"reais_por_xm": "1e3"}` escrito a mao passa por `json.loads` sem esforco. Se a leitura confiasse no arquivo por ele ser "nosso", todo o portao de duas camadas viraria enfeite contornavel por um editor de texto — e T-01-13 nomeia exatamente a edicao a mao como vetor.
- **Fix:** `ler_o_cambio` passa o valor guardado por `interpretar_o_cambio`, o mesmo ponto de entrada do formulario. Falha vira nulo com aviso, sem apagar o arquivo.
- **Files modified:** `l2scanner/dashboard_cambio.py`, `tests/test_dashboard_cambio.py`
- **Verification:** `test_um_valor_ILEGAL_editado_a_MAO_no_arquivo_devolve_NULO`
- **Committed in:** `25225f3` (RED) e `4b19472` (GREEN)

---

**Total deviations:** 2 auto-fixed (2 missing critical, ambos no eixo "nao destruir dado do usuario")
**Impact on plan:** Nenhum scope creep. As duas fecham buracos no caminho que o plano nao especificou, e as duas estao dentro dos limites travados do proprio plano (nada e apagado; a falha e fechada; o portao mora no servidor). `requirements.txt` sem uma linha nova; nenhum arquivo do workstream `mercado` tocado.

## Issues Encountered

- **A tabela medida da pesquisa tinha uma linha errada, e a suite achou.** `'٠٫٥'` e `'０．５'` sao recusados por `Decimal`, mas por causa do **separador** Unicode — nao do digito. Escrever o teste como "digito Unicode e recusado pelas duas camadas" e medir revelou que `Decimal('٥')` vale **5** e que `\d` sem `re.ASCII` casa com ele. A conclusao da pesquisa (usar `re.ASCII`) continua certa; o **motivo** dela estava subestimado, e a correcao esta no comentario do molde com o valor medido ao lado, mais dois testes.
- **Nenhum outro.** A suite completa fecha em `4.560 passed, 25 skipped`, `git status --porcelain .mercado/` sai vazio, e `find` confirma que nenhum `cambio.json` foi criado fora de `tmp_path`.

## User Setup Required

None — nenhuma configuracao de servico externo. `.mercado/cambio.json` nasce sozinho na primeira vez que o usuario salvar uma taxa pela pagina.

## Next Phase Readiness

**Pronto para quem consumir:**
- `ler_o_cambio(pasta) -> Cambio | None` e `gravar_o_cambio(pasta, texto, agora) -> Cambio` sao o par que o **01-05** liga no `POST /cambio` e no endpoint de dados. O `Cambio` carrega valor **e** carimbo — os dois sao obrigatorios na tela pelo DASH-02.
- **O cambio entra no `payload` por PARAMETRO.** `dashboard_cambio` nao importa `dashboard_dados` e vice-versa; quem junta os dois e o servidor. Ha criterio do plano prendendo isso por AST. Preservar essa separacao e o que mantem `payload` testavel sem disco.
- `CambioInvalido` carrega **sempre** `MENSAGEM_DE_CAMBIO_INVALIDO`. O handler do `POST` deve devolver essa string como recebeu — reescreve-la no navegador seria o segundo formatador que o DASH-03 proibe.
- `HistoricoDoCambioIlegivel` e uma **segunda** falha possivel no `POST` e precisa de resposta propria: ela nao e culpa do que o usuario digitou, e a frase de cambio invalido mentiria sobre a causa.

**O que o proximo planejador precisa saber:**
- `interpretar_o_cambio` devolve `Decimal`, e **JSON nao tem `Decimal`**. Na hora de por o R$ no payload, a conversao para `float` (ou, melhor, para string ja formatada) tem de ser declarada em voz alta no ponto exato, como este modulo declara na gravacao.
- O `maxlength` do campo no HTML (01-07) deve casar com `TETO_DE_DIGITOS_INTEIROS + 1 + TETO_DE_CASAS_DECIMAIS`. O servidor nao acredita no `maxlength` — mas um campo que deixa digitar o que o servidor vai recusar e uma frustracao evitavel.

## Self-Check: PASSED

- **Arquivos criados:** `l2scanner/dashboard_cambio.py` e `tests/test_dashboard_cambio.py` conferidos no disco — ambos presentes.
- **Commits:** `4f38989`, `3f960a4`, `25225f3`, `4b19472` conferidos no `git log 73f99a7..HEAD`.
- **Suite:** `python -m pytest tests/ -q` → **4.560 passed, 25 skipped**, 0 falhas.
- **Plano, `<verification>` item a item:** `pytest tests/test_dashboard_cambio.py -q` → 43 passed (criterio pedia ≥14); `pytest tests/ -q` → 0; `git status --porcelain .mercado/` → vazio; `git diff --stat requirements.txt` → vazio.
- **Criterios de aceitacao executaveis:** o `python -c` da mensagem travada sai 0; o `python -c` do AST (nenhum import de `dashboard_dados`) sai 0.
- **Cerca de escopo:** `git status --short` mostra apenas os dois arquivos deste plano. `rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`, `config.py`, `mercado_catalogo.py` e `requirements.txt` intocados.
- **Lint:** `ruff check` nos dois arquivos → `All checks passed!`.
- **Nenhuma escrita fora de `tmp_path`:** `find . -name "cambio.json*"` apos a suite completa → vazio.

## Known Stubs

Nenhum stub. O modulo esta completo para o que o DASH-02 exige do lado do servidor. O que falta para o requisito fechar na TELA — o `POST /cambio`, o campo no HTML e a frase de erro desenhada — e dos planos 01-05 e 01-07, e nao ha aqui nenhum valor fabricado, nenhum padrao chutado e nenhum componente recebendo dado vazio. A ausencia de cambio e representada por `None`, com palavra na tela, nunca por `0,00`.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-02*
