---
status: resolved
trigger: "Regressao da Fase 2 do workstream mercado, descoberta durante a Fase 3: tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida falha. 1 failed, 144 passed."
created: 2026-08-31
updated: 2026-08-31 (resolvido)
workstream: mercado
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

bug_class: "Heisenbug (Mandelbug) — o desfecho depende do layout do heap, nao da producao. Instrumentar o caso o faz sumir: qualquer wrapper em `__call__` deixa a suite VERDE."
hypothesis: "CONFIRMADA. `LeitoraContadora.__call__` anota `id(pixels)` de recortes numpy TRANSITORIOS. O CPython recicla o endereco assim que o recorte de uma linha e liberado, entao dois recortes DIFERENTES aparecem com o mesmo `id` e o `set()` do teste os funde. `len(set(...))` passa a contar MENOS que as linhas, e `len(ambas) == len(leitura.linhas)` falha sem que a producao tenha mudado."
test: "Medir o que NAO depende do alocador (chamadas, len das listas, igualdade posicional) e comparar 8b87eb3 (verde) com efcd73a (vermelho)."
expecting: "Se a producao regrediu, `chamadas` ou `len(vistos_3x)` divergem de `len(leitura.linhas)`. Deram 6/6/6 nos DOIS commits -> producao intacta."
next_action: "Aplicar o conserto: segurar referencia forte aos recortes em `LeitoraContadora`, sem tocar em nenhuma afirmacao. Depois suite inteira + repeticao para provar determinismo."

reasoning_checkpoint:
  hypothesis: "O teste usa `id()` de recortes transitorios como identidade estavel e depois deduplica com `set()`. Enderecos reciclados fundem recortes distintos, e a contagem cai abaixo do numero de linhas."
  confirming_evidence:
    - "Sonda: um unico `id` carregou QUATRO conteudos (sha1) distintos; varios carregaram 2 e 3."
    - "Medidas insensiveis ao alocador, identicas em 8b87eb3 e efcd73a: linhas aceitas=6, barata.chamadas=6, conferencia.chamadas=6, len(vistos_2x)=len(vistos_3x)=6, vistos_2x==vistos_3x=True."
    - "So o artefato do alocador varia: len(set(vistos_2x)) deu 4 (8b87eb3), 5 (efcd73a) e 6 (rodando a classe sozinha) — sem que nada de significativo mudasse."
    - "O corpo do teste e o `LeitoraContadora.__call__` sao BYTE-IDENTICOS em 8b87eb3 e em HEAD (a linha `id(pixels)` e a 187 nos dois)."
    - "Sitio de producao incondicional: `barato = ler_texto(recorte_do_nome)` seguido de `caro = ler_texto_conferencia(recorte_do_nome)` — mesmo objeto, sem desvio que possa pular uma das duas."
  falsification_test: "Se a producao tivesse passado a ler com UMA escala so, `conferencia.chamadas` seria 0 (ou != linhas aceitas) e `vistos_3x` viria vazia/curta. Deu exatamente 6 == 6 == 6 -> hipotese de regressao de producao REFUTADA."
  fix_rationale: "Segurar referencia forte a cada recorte impede a reciclagem do endereco e devolve a `id()` o significado que as afirmacoes sempre presumiram. NENHUMA afirmacao muda, entao a invariante D-01/D-02 fica intacta — e o teste fica ESTRITAMENTE MAIS FORTE, porque `set()` so podia encolher a contagem (folga), e agora a igualdade e exata e deterministica."
  blind_spots: "Custo de memoria: 6 recortes pequenos presos por teste (irrelevante). `grep` confirmou que este e o UNICO uso de `id()` como identidade em toda a suite, entao a classe de defeito nao tem irmaos escondidos."
  candidate_causes:
    - "code (teste): `id()` como identidade estavel — CONFIRMADA"
    - "code (producao): uma das duas leitoras deixou de ser chamada — REFUTADA (6==6==6)"
    - "environment: layout do heap / reciclagem de endereco pelo alocador — GATILHO, nao causa"
    - "data: fixtura ou calibracao mudaram — REFUTADA (md5 intacto, fixturas versionadas sem diff)"
  and_gate: "SIM — precisa das DUAS condicoes ao mesmo tempo: (a) a identidade insegura do teste E (b) um padrao de alocacao que recicle um endereco. Nenhuma das duas sozinha derruba o teste. E exatamente por isso ele ficou VERDE desde que nasceu ate o estabilizador do efcd73a mexer no heap."

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: |
  O teste exige `len(ambas) > 0` — ao menos uma linha das 10 tem de virar `LinhaLida`,
  e nela as DUAS leitoras (duas escalas de OCR) tem de ter sido CHAMADAS e confrontadas.

actual: |
  Nenhuma das 10 linhas vira `LinhaLida`. Todas as 10 sao recusadas na coluna Total.
  `len(ambas) == 0` -> assert falha.

errors: |
  FAILED tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida
  1 failed, 144 passed

  Para cada uma das 10 linhas:
  WARNING l2scanner.mercado_leitura:1615 linha N RECUSADA (numero): a coluna Total nao se leu inteira

reproduction: |
  Python GLOBAL (nao o .venv):
    python -m pytest tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida -v
  Deterministico. Reproduz em isolamento e em processo limpo.

started: |
  Descoberto na Fase 3. A Fase 2 fechou declarando "2605 passed, 2 skipped, zero failed" —
  ou a medicao nao alcancou este arquivo, ou foi feita antes do commit final.
  De um jeito ou de outro, a fase fechou vermelha sem saber.

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-08-31 (pre-apurado pelo usuario, NAO REFAZER)
  checked: Determinismo e escopo da falha
  found: |
    - Deterministico; reproduz em isolamento e em processo limpo.
    - SO ESTE teste cai. Os outros 144 do mesmo arquivo passam, INCLUSIVE os vizinhos
      da mesma classe TestOAcordoEntreAsDuasEscalas.
  implication: |
    Nao e ambiente, nao e ordem de teste, nao e poluicao de estado entre testes.
    O defeito e especifico ao caminho que ESTE teste exercita.

- timestamp: 2026-08-31 (pre-apurado pelo usuario, NAO REFAZER)
  checked: Integridade de todas as entradas do teste
  found: |
    - calibration.json intacto (md5 1d6b9b6b051408e3, o mesmo de quando a Fase 2 fechou).
    - Tudo que o teste consome e VERSIONADO e nao mudou:
      tests/fixtures/mercado/calibracao_de_fixture.json
        (mercado_limiar_de_brilho_da_quantidade=161,
         mercado_folga_de_cola_do_glifo=1,
         mercado_limiar_de_leitura_de_glifo=0.4698309302330017)
      tests/fixtures/mercado/janela_negociacao_f010.png
    - Nada tocou l2scanner/mercado_leitura.py desde o fim da Fase 2.
  implication: |
    As ENTRADAS sao identicas. Logo a mudanca de comportamento veio de CODIGO,
    e nao do modulo que emite o warning (mercado_leitura.py) — veio de algum
    colaborador dele.

- timestamp: 2026-08-31 (pre-apurado pelo usuario, NAO REFAZER)
  checked: Suspeito principal por diff de tamanho
  found: |
    Commit efcd73a ("feat(02-05): o estabilizador completo — congelamento e acordo
    por intersecao") levou l2scanner/mercado_pagina.py de 504 para 761 linhas.
    O teste monta um LeitorDePagina, que vive nesse modulo.
    Ponto bom conhecido ANTES dele: 8b87eb3.
  implication: |
    Candidato forte para bisect: efcd73a. Bisect entre 8b87eb3 (bom) e efcd73a/HEAD (ruim)
    confirma ou elimina em poucos passos. NAO aceitar "provavelmente o estabilizador"
    como causa-raiz — tem de ser PROVADO.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "CORRECAO DO SINTOMA RELATADO. Rodei o arquivo em HEAD e no proprio commit do usuario (46c15a5)."
  found: |
    O sintoma relatado NAO e o sintoma real. Nos dois pontos a falha e a MESMA e e:
      assert len(ambas) == len(leitura.linhas)  ->  AssertionError: assert 5 == 6
    e nao `len(ambas) > 0`. E as linhas recusadas sao QUATRO (0,1,2,3), nao dez:
      descartadas=(0,1,2,3), motivos=('numero',)*4, 6 linhas ACEITAS.
  implication: |
    "Nenhuma linha vira LinhaLida" era leitura equivocada da saida: seis viram.
    E as 4 recusas por 'numero' sao COMPORTAMENTO DOCUMENTADO E CORRETO — a
    docstring do modulo de teste ja registra que neste frame a tooltip cobre a
    coluna Total das linhas 0 a 3. Nao ha defeito nenhum nessa parte.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "Sonda de identidade: (id, sha1) de cada recorte entregue as leitoras."
  found: |
    `id()` NAO e identidade estavel aqui. Um unico id carregou QUATRO conteudos
    distintos; varios carregaram 2 e 3. E a propria sonda, so por existir,
    deixou a suite VERDE (145 passed) — e um wrapper vazio em `__call__`
    tambem deixa.
  implication: |
    Heisenbug: o desfecho depende do layout do heap. Uma regressao de leitura
    de verdade nao sumiria por causa de um wrapper vazio.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "Medidas INSENSIVEIS ao alocador em 8b87eb3 (verde) e efcd73a (vermelho)."
  found: |
    IDENTICAS nos dois commits:
      linhas aceitas ....... 6        barata.chamadas ...... 6
      conferencia.chamadas . 6        len(vistos_2x/3x) .... 6 / 6
      vistos_2x == vistos_3x = True   descartadas .......... (0,1,2,3)
    So o artefato do alocador variou: len(set(vistos_2x)) = 4 em 8b87eb3,
    5 em efcd73a, 6 rodando a classe sozinha.
  implication: |
    A producao NAO mudou naquilo que o teste afirma medir. As duas leitoras
    foram chamadas uma vez por linha aceita, com o MESMO objeto e na mesma
    ordem, nos dois lados da fronteira. VEREDITO: o teste e que estava errado.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "Bisect por git archive (sem checkout, arvore compartilhada intocada)."
  found: |
    8b87eb3 -> 145 passed (e o teste JA EXISTE la).
    efcd73a -> 1 failed.  Introdutor confirmado.
    Porem: `git diff 8b87eb3 efcd73a -- tests/` mostra que o corpo do teste,
    o `LeitoraContadora.__call__` e o `montar_leitor` sao BYTE-IDENTICOS.
    efcd73a mudou so producao (+317 linhas em mercado_pagina.py).
  implication: |
    efcd73a e GATILHO, nao causa. O defeito nasceu junto com o teste e ficou
    dormindo ate o estabilizador mexer no padrao de alocacao.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "Conferencia por MUTACAO, com o conserto ja aplicado."
  found: |
    Mutante 1 (caro = ler_texto(...), uma escala so): 8 testes morrem, o alvo
      com `assert 0 == 6`. Mutante 2 (conferencia recebe .copy()): 2 morrem.
    Revertidos os mutantes: 145 passed.
  implication: |
    A invariante D-01/D-02 continua sendo guardada de verdade. O conserto NAO
    afrouxou nada — o teste segue matando exatamente o defeito para o qual nasceu.

- timestamp: 2026-08-31 (medido nesta sessao)
  checked: "A contagem de fechamento do 02-05, remedida em efcd73a."
  found: |
    efcd73a real: 1 failed, 2551 passed, 14 skipped (sem test_agenda.py)
    e 144 passed so com ele = 2695 passed, 14 skipped, UMA falha.
    O SUMMARY afirma 2605 passed, 2 skipped, zero falhas.
  implication: |
    Nem total, nem skips, nem zero-falhas batem: a contagem nao foi tirada em
    efcd73a. A fase fechou vermelha sem saber. Corrigido no 02-05-SUMMARY.md
    e no 02-VERIFICATION.md, e registrado como janela #38.

## Eliminated
<!-- APPEND only - prevents re-investigating -->

- hypothesis: "calibration.json ou as fixtures mudaram / corromperam"
  evidence: "md5 do calibration.json inalterado; fixtures versionadas e sem diff. Pre-apurado pelo usuario."
  timestamp: 2026-08-31

- hypothesis: "mercado_leitura.py regrediu (e o modulo que emite o warning)"
  evidence: "Nada tocou l2scanner/mercado_leitura.py desde o fim da Fase 2. Pre-apurado pelo usuario."
  timestamp: 2026-08-31

- hypothesis: "Poluicao de estado entre testes / ordem de execucao / flake"
  evidence: "Reproduz deterministicamente em isolamento e em processo limpo. Pre-apurado pelo usuario."
  timestamp: 2026-08-31

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  O TESTE, nao a producao. `LeitoraContadora.__call__` anotava `id(pixels)` de
  recortes numpy TRANSITORIOS, e o teste deduplicava com `set()`. O CPython
  recicla o endereco assim que o recorte de uma linha e liberado, entao recortes
  DIFERENTES apareciam com o mesmo `id` e o `set()` os fundia — `len(set(...))`
  passava a contar MENOS que as linhas aceitas.
  E um AND de duas condicoes: (a) a identidade insegura do teste E (b) um padrao
  de alocacao que recicle um endereco. Por isso ficou verde desde que nasceu.
  `efcd73a` (o estabilizador do 02-05) foi o GATILHO: mudou a alocacao, nao a
  leitura. O corpo do teste e o `__call__` sao byte-identicos antes e depois.

fix: |
  `tests/test_mercado_leitura.py`: `LeitoraContadora` passou a segurar uma
  referencia forte a cada recorte (`self._vivos`), o que impede a reciclagem do
  endereco e devolve a `id()` o significado que as afirmacoes sempre presumiram.
  NENHUMA afirmacao foi tocada. O porque esta escrito em comentario no proprio
  helper, para nao voltar.

verification: |
  - Arquivo: 145 passed. Suite: 2794 passed, 2 skipped (sem test_agenda.py)
    + 145 passed (so ele) = ZERO falhas.
  - Determinismo: 10 sementes de PYTHONHASHSEED, todas 145 passed; e verde
    tambem com a classe sozinha e com o teste sozinho (contextos que antes
    davam resultados diferentes).
  - Mutacao (o guardiao ainda morde): escala unica mata 8 testes, o alvo com
    `assert 0 == 6`; `.copy()` na conferencia mata 2.
  - Producao provada correta ANTES de tocar o teste: medidas insensiveis ao
    alocador identicas em 8b87eb3 e efcd73a (6/6/6, vistos_2x == vistos_3x) e
    sitio incondicional em mercado_leitura.py:1537-1538.

files_changed:
  - tests/test_mercado_leitura.py (unico arquivo de codigo; +2 linhas e um comentario)
  - .planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-05-SUMMARY.md (correcao da contagem)
  - .planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-VERIFICATION.md (mesma correcao)
  - .planning/WINDOWS.md (janela #36 fechada; #37 e #38 registradas e fechadas)

## Contrato do Teste (por que ele NAO pode ser afrouxado)

Este teste e o criterio CENTRAL da decisao travada **D-01/D-02 da Fase 2**:
**o nome e lido DUAS vezes, por duas escalas de OCR, e as duas leituras sao confrontadas.**

Docstring do teste:
> "Um `ler_linha` que lesse com uma escala so faz este teste FALHAR — e e exatamente
> o defeito que ele existe para pegar, porque uma leitura unica tambem produz
> `LinhaLida` valida e todos os outros criterios a aprovariam."

Ele nasceu depois de o plan-checker mostrar que o mecanismo estava **implicado por uma
assinatura de construtor** e nao construido.

**REGRA:** ele nao pode ser afrouxado nem adaptado ao comportamento novo sem PROVA de que
o comportamento novo e o certo. Se o veredito for "o teste ficou desatualizado", a prova de
que a mudanca de producao e correta tem de vir ANTES de tocar o teste, e a razao vai escrita.

## Restricoes Inegociaveis

- NAO afrouxar o teste para ficar verde.
- NAO tocar `l2scanner/rastreador.py` nem o gate de brilho da barra propria em `l2scanner/visao.py`.
- NAO desfazer o D-17 da Fase 3 (nada de `truncate`, nada de reparar bytes no caminho de leitura)
  nem nada de `l2scanner/mercado_registro.py`.
- **Arvore compartilhada:** outro agente trabalha nos workstreams `tiat`/`identidade` NESTA MESMA
  ARVORE, em paralelo. NAO tocar: `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`,
  `config.toml`, `test_bosses.py`, `.planning/workstreams/tiat|identidade/`.
- **NUNCA `git commit --amend`.**
- NUNCA commitar `calibration.json`. `recordings/` e somente leitura.
- Nenhuma dependencia nova.
- Toda chamada a `gsd-tools` precisa de `--ws mercado`.

## Fatos Operacionais

- Pytest roda no **Python GLOBAL**, nao no `.venv`.
- **Flake conhecido:** `tests/test_agenda.py:1141` levanta `KeyboardInterrupt` de proposito e as vezes
  derruba a sessao. **Abortar nao e falhar** — rodar `--ignore=tests/test_agenda.py` e depois so ele.
- Estado agora: 1 failed em `tests/test_mercado_leitura.py`; o resto da suite verde.
- Usuario dormindo, trabalho autonomo autorizado. **Nao abrir pergunta.** Decidir, consertar,
  registrar a razao. Se a causa for algo que so ele pode decidir, PARAR e REGISTRAR em vez de improvisar.

## Entregaveis Exigidos

1. A causa-raiz **provada** (bisect se preciso; efcd73a e o candidato, 8b87eb3 e um ponto bom antes dele).
2. O **veredito** sobre quem esta errado: producao regrediu, ou o teste ficou desatualizado?
3. O **conserto**, com o teste passando pelo motivo certo e a suite inteira verde.
4. **Registro:** entrada no `.planning/WINDOWS.md`, e nota no `02-05-SUMMARY.md` dizendo que a
   contagem "2605 passed / zero failed" dele nao se sustenta — um numero que caiu precisa dizer que caiu.
