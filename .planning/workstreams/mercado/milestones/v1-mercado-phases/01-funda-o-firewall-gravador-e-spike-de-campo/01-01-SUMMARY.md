---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 01
subsystem: infra
tags: [gravador, cv2-imwrite, importlib-metadata, supply-chain, argparse, pytest]

requires: []
provides:
  - "Gravador.gravar() -> bool: contador, observacoes.jsonl e resumo final atras do MESMO portao da escrita confirmada"
  - "Gravador.falhas_de_gravacao: contagem de escritas nao confirmadas, com erro ALTO na primeira e a cada 10"
  - "Gravador(fonte_completa=...): modo de gravacao da JANELA COMPLETA, que falha FECHADA quando a janela nao produz frame"
  - "flag CLI --record-janela (implica --record, exige --janela, recusa --replay)"
  - "resumo final de gravacao com tres numeros: confirmados, falhas e a contagem lida do disco"
  - "tests/test_firewall_escopo.py: FIRE-01 com tres varreduras + prova do vermelho sem instalar nada"
affects: [01-02 roteiro do spike, 01-03 respostas do spike, 01-04 calibracao de mercado, qualquer fase que grave sessao]

actuals:
  tokens: 27894
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Escrita de imagem checada (falha fechada): bool(cv2.imwrite) + try/except no MESMO caminho de falha, replicado de calibrar._gravar_conferencia"
    - "Contagem independente lida do disco ao lado do contador, para tornar a auditoria trivial"
    - "Firewall de supply chain como teste da suite normal, varrendo os DOIS ambientes Python + o requirements.txt declarado"
    - "Prova de detector por mutacao e por artefato fabricado, nunca instalando o que se quer proibir"

key-files:
  created:
    - tests/test_gravador_honesto.py
    - tests/test_firewall_escopo.py
  modified:
    - l2scanner/gravador.py
    - l2scanner/__main__.py

key-decisions:
  - "O log ALTO da falha mora em gravador.py, nao em Sessao.tick: o modulo que possui a verdade do disco e o que reporta a mentira, e assim sessao.py fica byte-identico"
  - "Supressao de log: grita na PRIMEIRA falha e a cada 10 acumuladas; com disco cheio a 1 Hz um erro por volta enterraria os alertas de party, que sao o produto"
  - "A contagem lida do disco usa is_file(): um diretorio com nome de PNG (o modo de falha deterministico dos testes) seria contado por um glob cru, reintroduzindo a mentira dentro da propria conferencia"
  - "--record-janela nao cai de volta em frame.pixels quando a janela nao produz frame: gravar o recorte errado em silencio gastaria as sessoes do usuario, o recurso escasso da fase"
  - "A validacao de --replay vem ANTES da de --janela: com sessao gravada nao existe janela, e mandar acrescentar --janela seria conselho errado"
  - "O firewall prova o vermelho por mutacao E por dist-info fabricada em tmp_path; instalar uma banida de verdade num teste seria cometer o proprio pecado"

patterns-established:
  - "Portao unico para saidas correlacionadas: contador, indice e resumo nunca podem divergir porque passam pelo mesmo if"
  - "Toda constante de limiar/supressao carrega a medicao ao lado no fonte (3,5 MB/frame, ~210 MB/min, 1 Hz)"
  - "Varredura de dependencia por importlib.metadata.distributions(path=...) para alcancar um interpretador que nao e o corrente"

requirements-completed: [FUND-01, FIRE-01, FUND-02]

coverage:
  - id: D1
    description: "Gravador so conta escrita CONFIRMADA — contador, observacoes.jsonl e resumo atras do mesmo portao, e uma falha nunca levanta excecao"
    requirement: "FUND-01"
    verification:
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_o_caminho_feliz_conta_exatamente_o_que_esta_no_disco"
        status: pass
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_uma_escrita_que_falha_nao_conta_nem_indexa"
        status: pass
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_toda_linha_do_jsonl_cita_um_arquivo_que_existe"
        status: pass
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_gravar_nunca_levanta_nem_quando_o_imwrite_explode"
        status: pass
    human_judgment: false
  - id: D2
    description: "A falha de gravacao aparece como erro ALTO citando o arquivo que falhou"
    requirement: "FUND-01"
    verification:
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_a_falha_de_escrita_aparece_como_erro_alto"
        status: pass
    human_judgment: false
  - id: D3
    description: "O resumo final da sessao imprime frames confirmados, falhas e a contagem independente lida do disco"
    requirement: "FUND-01"
    verification: []
    human_judgment: true
    rationale: "O bloco vive no `finally` de `laco_principal`, que so roda com uma sessao de verdade (jogo aberto ou replay completo). Nenhum teste da suite exercita esse caminho hoje, e o valor do resumo e exatamente ser lido por um humano no fim de uma hora de farm — a human-check da Task 1 continua em aberto."
  - id: D4
    description: "Gravador com fonte_completa grava a JANELA COMPLETA, e falha FECHADA quando a janela nao produz frame (nunca grava o recorte da party como consolo)"
    requirement: "FUND-02"
    verification:
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_o_modo_janela_grava_a_janela_completa_e_nao_o_recorte"
        status: pass
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_a_janela_sem_frame_falha_fechada_em_vez_de_gravar_o_recorte"
        status: pass
      - kind: unit
        ref: "tests/test_gravador_honesto.py#test_sem_fonte_completa_o_comportamento_e_o_de_hoje"
        status: pass
    human_judgment: false
  - id: D5
    description: "A flag --record-janela recusa ALTO as combinacoes impossiveis (sem --janela, e junto de --replay)"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "python -m l2scanner --record-janela (exit 2, mensagem citando capturar_completo)"
        status: pass
      - kind: other
        ref: "python -m l2scanner --record-janela --replay recordings/inv3 (exit 2, mensagem citando sessao gravada)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Uma sessao real com --janela --record-janela produz PNGs da janela inteira do jogo (~3,5 MB), com o painel do mercado dentro"
    requirement: "FUND-02"
    verification: []
    human_judgment: true
    rationale: "Exige o jogo aberto na maquina do usuario — o gate externo declarado da fase. O sinal de alarme (PNG de ~170 KB no lugar de ~3,5 MB) so e observavel numa gravacao de verdade."
  - id: D7
    description: "Firewall FIRE-01: tres varreduras (requirements.txt declarado, ambiente da suite, .venv de producao) mais a transitiva declarada por Requires-Dist"
    requirement: "FIRE-01"
    verification:
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_o_requirements_declarado_nao_pede_biblioteca_de_input"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_o_ambiente_que_roda_a_suite_nao_tem_biblioteca_de_input"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_o_venv_de_producao_nao_tem_biblioteca_de_input"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_nenhuma_dependencia_instalada_declara_biblioteca_de_input"
        status: pass
    human_judgment: false
  - id: D8
    description: "O detector do firewall tem prova de vermelho sem que nenhuma biblioteca de input tenha sido instalada"
    requirement: "FIRE-01"
    verification:
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_o_detector_acusa_uma_distribuicao_banida_injetada"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_a_varredura_por_path_acusa_uma_dist_info_banida_fabricada"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_escopo.py#test_a_mensagem_de_falha_explica_o_porque"
        status: pass
    human_judgment: false
  - id: D9
    description: "Criterio 5 do ROADMAP visto com as proprias maos: `pip install keyboard` no .venv deixa a suite vermelha"
    requirement: "FIRE-01"
    verification: []
    human_judgment: true
    rationale: "A demonstracao ponta a ponta esta escrita na docstring de tests/test_firewall_escopo.py, mas NAO e automatizada por decisao: instalar uma biblioteca de sintese de input dentro de um teste seria cometer o proprio pecado que o teste existe para impedir. O mecanismo esta provado por D8; a confirmacao visual e do usuario."

duration: 8 min
completed: 2026-08-27
status: complete
---

# Phase 1 Plan 1: Fundacao — gravador honesto, janela completa e firewall de escopo Summary

**`Gravador.gravar` passou a devolver `bool` e a condicionar contador, `observacoes.jsonl` e resumo final a um `cv2.imwrite` confirmado; ganhou o modo `--record-janela` que grava a janela inteira do jogo (o pre-requisito do spike de mercado); e nasceu `tests/test_firewall_escopo.py`, que varre os TRES lugares onde uma biblioteca de sintese de input poderia entrar.**

## Performance

- **Duration:** ~8 min de execucao (primeiro commit 20:31:47, ultimo 20:40:05), ~25 min com leitura de contexto
- **Started:** 2026-08-27T23:15:00Z (aprox.)
- **Completed:** 2026-08-27T23:40:05Z
- **Tasks:** 3 de 3
- **Files modified:** 4 (2 criados, 2 alterados)

## Accomplishments

- **O gravador parou de mentir.** Antes, `frames_gravados += 1` acontecia na TENTATIVA: com a escrita falhando, o contador, a linha do `observacoes.jsonl` (citando um arquivo inexistente) e o resumo final mentiam juntos. Agora as tres saidas ficam atras do mesmo `if`, e o resumo imprime a contagem lida do disco ao lado do contador — a auditoria virou uma olhada em duas colunas.
- **A falha e visivel e nao derruba nada.** `gravar` nunca levanta (o `tick` roda sem `try/except` no laco principal, entao uma excecao por disco cheio mataria os alertas de morte da party junto), loga `ERROR` na primeira falha e a cada 10 acumuladas, e o resumo sobe para `ERROR` quando houve qualquer perda.
- **`--record-janela` destravou o spike.** O `--record` de hoje salvava so o recorte de 172x522 da party window: uma sessao gravada nao continha UM PIXEL do painel do mercado. O modo novo grava a janela completa via `JanelaSource.capturar_completo`, e quando a janela nao produz frame ele falha FECHADO — nunca grava o recorte errado em silencio.
- **FIRE-01 virou portao executavel.** O `requirements.txt` ja pedia por escrito que ninguem adicionasse `pyautogui` e companhia; agora ha um teste na suite normal que varre o `requirements.txt` declarado, o ambiente que roda a suite (o Python GLOBAL) e o `.venv` de producao (via `distributions(path=...)`) — o buraco que uma varredura unica deixaria aberto.

## Task Commits

1. **Task 1 (RED): provas do gravador honesto** — `5930947` (test)
2. **Task 1 (GREEN): escrita confirmada + resumo com a verdade do disco** — `e85fcea` (feat)
3. **Task 2: `--record-janela` e o modo janela completa** — `724ae4d` (feat)
4. **Task 3: firewall de escopo com as tres varreduras** — `dcddf48` (feat)

## Files Created/Modified

- `l2scanner/gravador.py` — `gravar() -> bool`, `falhas_de_gravacao`, `_escrever` (padrao `calibrar._gravar_conferencia`), `_contabilizar_falha` com supressao, parametro `fonte_completa`, docstrings com o comportamento e o custo MEDIDOS
- `l2scanner/__main__.py` — flag `--record-janela` (implica `--record`, exige `--janela`, recusa `--replay`), fiacao de `fonte.capturar_completo` no `Gravador`, arranque citando o custo de disco, resumo final com os tres numeros
- `tests/test_gravador_honesto.py` (novo, 257 linhas) — 9 testes: caminho feliz, falha deterministica, JSONL sem orfaos, erro alto, nao-levanta, janela completa, janela sem frame, compatibilidade do `--record`, contrato estrutural
- `tests/test_firewall_escopo.py` (novo, 290 linhas) — 8 testes: as tres varreduras, transitiva declarada, mutacao do detector, dist-info fabricada, mensagem que explica, e o bloco de aviso do `requirements.txt` no lugar

## Decisions Made

- **O log ALTO mora em `gravador.py`, nao em `Sessao.tick`.** O modulo que possui a verdade do disco e o que reporta a mentira. Consequencia direta: `sessao.py` ficou byte-identico, e o raio de alcance do fix ficou em um modulo (D-09).
- **Supressao de log a cada 10 falhas.** A gravacao roda a ~1 Hz durante o farm; com disco cheio, um `ERROR` por volta viraria milhares de linhas identicas que enterram os alertas de party. Primeira falha grita, depois a cada dez, e o total exato nunca se perde: o resumo o reporta.
- **`is_file()` na contagem do disco.** Ver "Deviations" #1 — um `glob` cru contaria como frame gravado exatamente o artefato que os testes usam para provocar a falha.
- **Nunca cair de volta em `frame.pixels`.** As sessoes do usuario sao o recurso escasso da fase (so ele pode grava-las) e ele so descobriria o engano depois de gastar todas as oito.
- **`--replay` e checado antes de `--janela`.** Com uma sessao gravada nao existe janela nenhuma; mandar o usuario acrescentar `--janela` seria conselho errado.
- **Prova do firewall por mutacao e por artefato fabricado, jamais por instalacao.** Instalar `keyboard` dentro de um teste automatizado seria cometer o proprio pecado que o teste existe para impedir.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A "verdade do disco" contava diretorios como frames**

- **Found during:** Task 1 (o teste `test_toda_linha_do_jsonl_cita_um_arquivo_que_existe` ficou vermelho com `8 == 9`)
- **Issue:** O plano especifica `len(list(pasta.glob("frame_*.png")))` como contagem independente. Mas o modo de falha deterministico — um DIRETORIO ocupando o nome `frame_000007.png` — casa com esse glob. A conferencia que existe para provar que o contador nao mente contaria o proprio artefato da mentira como frame gravado.
- **Fix:** Filtro `is_file()` nos dois lugares: no helper `_pngs_no_disco` do teste e no `sum(...)` do resumo final em `__main__.py`, com o porque no comentario.
- **Files modified:** `l2scanner/__main__.py`, `tests/test_gravador_honesto.py`
- **Verification:** `test_toda_linha_do_jsonl_cita_um_arquivo_que_existe` passa afirmando `frames_gravados == len(_pngs_no_disco(pasta))` numa sessao mista
- **Committed in:** `e85fcea`

**2. [Rule 2 - Missing Critical] O teste-do-teste provava o predicado, nao o mecanismo**

- **Found during:** Task 3
- **Issue:** A mutacao especificada (`_banidas_presentes({"numpy", "opencv-python", "keyboard"})`) prova que a funcao de decisao decide certo. Ela nao prova que `_nomes_de` + `distributions(path=...)` chegam a VER o que existe no disco — e essa e justamente a metade que carrega o `.venv` de producao, onde o `pytest` nao roda. Um `_nomes_de` quebrado devolveria conjunto vazio e as tres varreduras ficariam verdes com uma banida instalada: exatamente o Pitfall 3 da RESEARCH, so que um nivel mais fundo.
- **Fix:** `test_a_varredura_por_path_acusa_uma_dist_info_banida_fabricada` — fabrica um `keyboard-0.13.5.dist-info` em `tmp_path` e afirma que a varredura por `path=` o enxerga e o acusa. Zero instalacoes.
- **Files modified:** `tests/test_firewall_escopo.py`
- **Verification:** o teste passa; verificado tambem fora da suite antes de escrever (a varredura devolveu `{'keyboard'}`)
- **Committed in:** `dcddf48`

**3. [Rule 2 - Missing Critical] O erro de falha nao distinguia as duas causas**

- **Found during:** Task 2
- **Issue:** Com `--record-janela`, uma janela que nao produz frame produziria a mesma mensagem de um `imwrite` que falhou. O usuario procuraria disco cheio quando o problema e a janela (minimizada, por exemplo).
- **Fix:** `_contabilizar_falha(caminho, motivo)` — `"o cv2.imwrite nao confirmou a escrita"` vs `"a janela nao produziu frame"`.
- **Files modified:** `l2scanner/gravador.py`
- **Verification:** `test_a_falha_de_escrita_aparece_como_erro_alto` e `test_a_janela_sem_frame_falha_fechada_em_vez_de_gravar_o_recorte` passam
- **Committed in:** `724ae4d`

**4. [Rule 1 - Bug] Ordem das recusas de argparse dava conselho errado**

- **Found during:** Task 2 (verificacao do criterio de aceite `--record-janela --replay`)
- **Issue:** Com as duas flags erradas juntas, a checagem de `--janela` disparava primeiro e mandava o usuario acrescentar `--janela` a um comando de replay — onde janela nenhuma existe.
- **Fix:** `--replay` e checado antes de `--janela`, com o porque no comentario.
- **Files modified:** `l2scanner/__main__.py`
- **Verification:** `python -m l2scanner --record-janela --replay recordings/inv3` sai com exit 2 e a mensagem correta
- **Committed in:** `724ae4d`

**5. [Rule 2 - Missing Critical] O corte de comentarios nao tinha guarda**

- **Found during:** Task 3
- **Issue:** A varredura declarada so e uma prova real porque o `requirements.txt` CITA os nomes banidos dentro de um comentario. Se alguem apagar esse bloco, o corte de comentarios deixa de ser exercitado por dados reais e o teste passa a provar menos do que promete — silenciosamente.
- **Fix:** `test_o_bloco_de_aviso_do_requirements_continua_no_lugar` prende o bloco e reafirma que a varredura declarada fica verde com ele presente.
- **Files modified:** `tests/test_firewall_escopo.py`
- **Verification:** o teste passa; `requirements.txt` nao foi alterado
- **Committed in:** `dcddf48`

---

**Total deviations:** 5 auto-fixed (2 bugs, 3 missing critical)
**Impact on plan:** Nenhum item do plano foi reduzido, adiado ou simplificado. As cinco correcoes fecham buracos que teriam deixado a propria verificacao mentir — que e o modo de falha que esta fase inteira existe para eliminar. Zero scope creep: nenhuma dependencia nova, `requirements.txt` intocado, `sessao.py` intocado, `calibrar.py` intocado.

## Portao do tracer

A Task 1 e `type="tracer"`. Com `mode: yolo` na config do projeto e `autonomous: true` no plano, o portao rodou em modo automatico: o `<verify>` da Task 1 foi re-executado ponta a ponta apos o commit (`tests/test_gravador_honesto.py tests/test_sessao.py tests/test_conferencia_gravada.py` — 66 passed) ANTES de qualquer task de expansao. Verde, entao a expansao seguiu.

## Issues Encountered

- **Anomalia transitoria do harness de shell, nao do codigo.** Duas execucoes encadeadas de `pytest` num unico laco `for` reportaram contagens estranhas (uma com 3 falhas, outra com "88 passed"). Investigado: seis execucoes consecutivas da suite completa deram `1181 passed, 2 skipped` sem excecao, e cada teste isolado passa. Nenhum defeito no codigo desta entrega.
- **`ruff check l2scanner/` acusa 2 `E741` PRE-EXISTENTES em `l2scanner/visao.py`** (variavel `l`). Fora do escopo desta task (o plano proibe tocar `visao.py`), nao introduzidas aqui. Todos os arquivos desta entrega passam limpos.

## Known Stubs

Nenhum. Nada nesta entrega retorna valor fixo, placeholder ou "coming soon"; todo caminho novo tem consumidor real e teste.

## Threat Flags

Nenhuma superficie de seguranca nova alem da ja registrada no `<threat_model>` do plano. T-01-01 (Tampering na arvore de dependencias) e T-01-02/T-01-03 (Repudiation/DoS no gravador) foram MITIGADAS conforme planejado; T-01-SC ficou vazio por construcao — zero instalacoes, `requirements.txt` byte-identico.

## User Setup Required

Nenhuma configuracao de servico externo. Restam DUAS conferencias humanas que dependem do jogo aberto (o gate externo declarado da fase):

1. **Task 1** — rodar com `recordings/` apontando para caminho invalido/somente-leitura por ~10 s: o console deve mostrar erro ALTO a cada falha, o resumo final deve dizer 0 confirmados / N falhas / 0 no disco, e o scanner deve continuar vivo o tempo todo.
2. **Task 2** — rodar 5 s com `--janela --record-janela --rotulo pre-voo` e abrir um PNG: deve ser a janela inteira do jogo, com cerca de **3,5 MB**. Um PNG de ~170 KB e o sinal de alarme do Pitfall 2 (voltou a gravar o recorte da party).

E, se quiser ver o criterio 5 do ROADMAP com as proprias maos:

```
.venv\Scripts\pip install keyboard
python -m pytest tests/test_firewall_escopo.py     -> VERMELHO
.venv\Scripts\pip uninstall keyboard
```

## Next Phase Readiness

- **O Bloco A esta pronto para o gate externo.** O gravador nao mente mais e sabe gravar a janela completa — as duas condicoes que o `ROTEIRO-SPIKE.md` (plano 01-02) precisa antes de o usuario gastar as sessoes.
- **FIRE-01 esta plantado antes de qualquer codigo de mercado**, que era o ponto: a restricao fundadora agora e estruturalmente verificada em todo `pytest`, nao apenas escrita.
- **Suite:** 1181 passed, 2 skipped (baseline antes do plano: 1164 passed, 2 skipped; +17 testes novos, zero regressoes).
- **Sem blockers novos.** O blocker da fase continua sendo o unico ja registrado no STATE: so o usuario pode gravar as sessoes reais do World Exchange.

## Self-Check: PASSED

- Arquivos criados/alterados conferidos no disco: `l2scanner/gravador.py`, `l2scanner/__main__.py`, `tests/test_gravador_honesto.py`, `tests/test_firewall_escopo.py` — todos FOUND
- Commits conferidos em `git log --all`: `5930947`, `e85fcea`, `724ae4d`, `dcddf48` — todos FOUND
- `<acceptance_criteria>` das 3 tasks re-executados e verdes
- `<verification>` do plano: suite verde (1181/2 skip, 6 execucoes consecutivas); `--record-janela` sem `--janela` e com `--replay` saem com exit 2 e razao dita; `requirements.txt` fora do diff; `l2scanner/sessao.py` fora do diff; zero delecoes de arquivo no intervalo do plano

---
*Phase: 01-funda-o-firewall-gravador-e-spike-de-campo (workstream mercado)*
*Completed: 2026-08-27*
