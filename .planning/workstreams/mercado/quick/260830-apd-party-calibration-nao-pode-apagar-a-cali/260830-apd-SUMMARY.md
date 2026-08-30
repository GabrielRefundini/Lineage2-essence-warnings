---
phase: quick-260830-apd
plan: 01
subsystem: calibracao
status: complete
tags: [calibracao, party, mercado, tiat, regressao, tdd, perda-de-dados]

requires:
  - "CR-04 (o mesmo conserto ja feito do lado do mercado: calibrar_mercado.calibrar carrega, muta so o que e seu, e grava)"
  - "l2scanner/calibracao.py (a dataclass Calibracao de 40 campos e o par salvar/carregar)"
provides:
  - "l2scanner.calibrar.CAMPOS_DA_PARTY — a lista de DONOS, de onde o preservado sai por subtracao"
  - "l2scanner.calibrar.fundir_com_a_calibracao_em_disco — o seam unico por onde --auto, --selecionar e _tentar_pelas_janelas_do_jogo passam"
  - "tests/test_calibrar_nao_apaga_mercado.py — 6 casos que prendem a invariante nos tres caminhos alcancaveis"
  - "Aviso alto NAO CONSEGUI PRESERVAR quando o calibration.json em disco esta ilegivel"
affects:
  - "Fase 2 (Leitura de pagina) — as 14 chaves gravadas pelo 02-01 agora sobrevivem a uma recalibracao de party"
  - "STATE.md do workstream mercado — JANELA 13 deixada ABERTA de proposito ate o human-check na maquina do usuario"
  - "Qualquer campo opcional criado no futuro — nasce PRESERVADO por omissao"

tech-stack:
  added: []
  patterns:
    - "Lista de DONOS, nunca de preservados: o conjunto a preservar sai por SUBTRACAO de dataclasses.fields(), entao campo novo nasce preservado e o esquecimento nao reproduz o incidente"
    - "Seam de fusao imediatamente antes do salvar, e nao dentro de Calibracao.salvar: quem le main() ve que existe uma leitura de disco, e calibrar_mercado (que ja carrega) nao funde duas vezes"
    - "O semeador do teste se prova por Calibracao.carregar ANTES de o teste acusar o codigo sob teste — um semeador invalido produziria o mesmo vermelho do defeito, pelo motivo errado"

key-files:
  created:
    - tests/test_calibrar_nao_apaga_mercado.py
  modified:
    - l2scanner/calibrar.py

key-decisions:
  - "A lista e de DONOS (13 campos da party) e o preservado sai por subtracao de dataclasses.fields(Calibracao) — uma lista de preservados exigiria que quem criasse o proximo campo opcional se lembrasse de inscreve-lo, e o esquecimento E o incidente"
  - "O dano medido e maior que mercado: banner_manutencao, tiat_chat e tiat_alvo tambem eram apagados. 40 campos, 13 da party, 27 preservados"
  - "Arquivo ilegivel NAO propaga: a party grava mesmo assim e avisa ALTO, porque essa e a rota de recuperacao do usuario — se ela parasse de gravar por causa de um arquivo ruim, ele ficaria sem saida"
  - "calibrar_tiat (linha ~1020) e o ramo --solo (linha ~1112) NAO foram tocados: os dois ja partem de Calibracao.carregar e ja preservavam. Consertar o que esta certo era o risco a evitar"
  - "O caso do --solo passa TAMBEM contra o codigo anterior ao conserto, medido de proposito: ele nao prova o conserto, prova a invariante"
  - "O caminho --tiat ficou sem caso por CUSTO (tres monkeypatches a mais), e nao por impossibilidade — escrito na docstring do modulo de teste"

patterns-established:
  - "Todo teste que dirige uma ferramenta de calibracao monkeypatcha ARQUIVO_CALIBRACAO para tmp_path, com o comentario NAO REMOVA e o motivo escrito"
  - "Portao de digest SHA-256 do calibration.json real antes/depois da suite, recusando quando o valor sai VAZIO — guarda vacua da confianca falsa"

requirements-completed: [JANELA-13, CR-04-PARTY]

coverage:
  - id: D1
    description: "Rodar a calibracao de party por --auto sobre um calibration.json com dados de mercado deixa os 27 campos que a party nao possui identicos ao que estava gravado"
    requirement: "JANELA-13"
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_auto_preserva_os_27_campos_que_a_party_nao_possui"
        status: pass
    human_judgment: false
  - id: D2
    description: "O mesmo por --selecionar, que delega para a mesma calibrar_automatico e cai no mesmo salvar"
    requirement: "JANELA-13"
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_selecionar_passa_pelo_mesmo_portao"
        status: pass
    human_judgment: false
  - id: D3
    description: "Os 13 campos que a party possui continuam recebendo o valor NOVO — nomes e assinaturas voltam a vazio sem --nomes, hp_proprio volta a None sem barra encontrada"
    requirement: "CR-04-PARTY"
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_os_13_campos_da_party_recebem_o_valor_NOVO_e_nao_o_do_disco"
        status: pass
    human_judgment: false
  - id: D4
    description: "CAMPOS_DA_PARTY e subconjunto da dataclass e nenhum campo mercado_ esta dentro dela"
    requirement: "CR-04-PARTY"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_a_lista_de_donos_e_coerente_com_a_dataclass"
        status: pass
    human_judgment: false
  - id: D5
    description: "Um calibration.json ilegivel nao impede a party de gravar — ela grava e avisa ALTO, nomeando o que nao conseguiu preservar"
    requirement: "JANELA-13"
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_arquivo_ilegivel_nao_impede_a_party_de_gravar_e_avisa_ALTO"
        status: pass
    human_judgment: false
  - id: D6
    description: "O caminho --solo continua preservando o mercado, e agora existe teste afirmando isso"
    requirement: "JANELA-13"
    verification:
      - kind: integration
        ref: "tests/test_calibrar_nao_apaga_mercado.py#test_solo_preserva_os_27_campos_e_muda_so_o_que_e_dele"
        status: pass
    human_judgment: false
  - id: D7
    description: "Com o conserto no lugar, uma rodada de calibrar.bat na MAQUINA DO USUARIO deixa os 13 moldes de glifo reais em pe"
    requirement: "JANELA-13"
    verification: []
    human_judgment: true
    rationale: "Nenhum teste tem os 13 moldes de verdade — eles so existem no calibration.json gitignored da maquina do usuario, cada um um arrasto de mouse mais um rotulo digitado. O `<human-check>` do plano pede a copia de seguranca ANTES da rodada; o plano ja custou os moldes uma vez."

metrics:
  duration: "~35 min"
  completed: 2026-08-30

actuals:
  tokens: 18432
  tasks: 3
  commits: 3

duration: 35min
completed: 2026-08-30
---

# Quick 260830-apd: A calibracao de party nao apaga mais a de mercado — Summary

**Seam de fusao em `l2scanner/calibrar.py` que carrega o `calibration.json` antes de gravar, com a lista de DONOS por subtracao de `dataclasses.fields`, e 6 casos que dirigem o `main()` de verdade e falhavam nomeando os 27 campos apagados.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3
- **Files modified:** 2 (1 criado, 1 modificado)

## Accomplishments

- Os 27 campos que a calibracao de party NAO possui — 24 `mercado_*` mais `banner_manutencao`, `tiat_chat` e `tiat_alvo` — sobrevivem a `--auto`, a `--selecionar` e a `--solo`.
- A lista no codigo e de **DONOS**, e o preservado sai por **subtracao** de `dataclasses.fields(Calibracao)`. Um campo opcional criado amanha nasce PRESERVADO, e nao apagado. O gate mediu: `OK 27 campos preservados`.
- Um `calibration.json` ilegivel deixou de ser um beco sem saida: a party grava mesmo assim e imprime `NAO CONSEGUI PRESERVAR`, nomeando o motivo, a calibracao de mercado e as regioes do Tiat.
- Os dois pontos de gravacao que ja estavam corretos (`calibrar_tiat` e o ramo `--solo`) ficaram **intactos** — o gate contou os tres `cal.salvar(ARQUIVO_CALIBRACAO)` continuando em 3.

## O PORTAO VERMELHO — a saida real, antes do conserto

Rodado no commit `93a9676` (teste dentro, conserto fora):

```
FAILED tests/test_calibrar_nao_apaga_mercado.py::TestAPartyNaoApagaOQueNaoEDela::test_auto_preserva_os_27_campos_que_a_party_nao_possui
FAILED tests/test_calibrar_nao_apaga_mercado.py::TestAPartyNaoApagaOQueNaoEDela::test_selecionar_passa_pelo_mesmo_portao
FAILED tests/test_calibrar_nao_apaga_mercado.py::TestAPartyNaoApagaOQueNaoEDela::test_a_lista_de_donos_e_coerente_com_a_dataclass
FAILED tests/test_calibrar_nao_apaga_mercado.py::TestAPartyNaoApagaOQueNaoEDela::test_arquivo_ilegivel_nao_impede_a_party_de_gravar_e_avisa_ALTO
4 failed, 1 passed, 1 warning in 0.24s
RC=1
RED CONFIRMADO
```

A mensagem do caso 1, com os 27 campos nomeados:

```
E  AssertionError: A calibracao de party APAGOU campos que nao sao dela:
   banner_manutencao, mercado_ancora, mercado_ancoras, mercado_cabecalho_de_coluna,
   mercado_coluna_da_quantidade, mercado_coluna_do_nome, mercado_coluna_do_total,
   mercado_coluna_do_unitario, mercado_corte_de_similaridade,
   mercado_geometria_da_captura, mercado_grade, mercado_limiar_da_ancora,
   mercado_limiar_de_dispersao_do_fundo, mercado_limiar_de_glifo,
   mercado_limiar_de_leitura_de_glifo, mercado_limiar_de_template,
   mercado_limiar_do_cabecalho, mercado_margem_de_leitura_de_glifo,
   mercado_minimo_de_linhas_comparadas, mercado_molde_da_ancora,
   mercado_piso_de_similaridade, mercado_sonda_do_fundo,
   mercado_templates_de_digito, mercado_templates_de_nome,
   mercado_tolerancia_do_cruzamento, tiat_alvo, tiat_chat
```

E o caso 4:

```
E  AttributeError: module 'l2scanner.calibrar' has no attribute 'CAMPOS_DA_PARTY'
```

**A cor de cada caso bateu com a tabela do plano, caso a caso:** 1 vermelho pelo dado ausente; 2 vermelho pelo mesmo motivo; **3 VERDE, e esperado** (guarda de regressao — o codigo de hoje ja monta os 13 campos do zero, entao nao ha o que ele denuncie antes do conserto); 4 vermelho por `AttributeError`; 5 vermelho pela ausencia do aviso alto. Nenhum caso foi reescrito para mudar de cor.

## Task Commits

1. **Task 1: o teste que falha hoje** — `93a9676` (test)
2. **Task 2: o seam de fusao** — `0c9038c` (fix)
3. **Task 3: prender tambem o `--solo`** — `6f723ef` (test)

## Files Created/Modified

- `tests/test_calibrar_nao_apaga_mercado.py` (novo, 465 linhas) — 6 casos que dirigem o `main()` de verdade com o disco preso a `tmp_path`.
- `l2scanner/calibrar.py` (+88, -1) — `fields` no import, `CAMPOS_DA_PARTY`, `fundir_com_a_calibracao_em_disco`, e a reatribuicao de `cal` no seam unico antes do `salvar` final.

## Decisions Made

- **Lista de DONOS, nao de preservados.** Uma lista de preservados exige que quem criar o proximo campo opcional se lembre de inscreve-lo; o esquecimento reproduz exatamente o incidente de 2026-08-30. Com DONOS, o default de um campo desconhecido e SOBREVIVER.
- **O seam fica onde o defeito esta, e nao dentro de `Calibracao.salvar`.** `salvar` e herdada por `calibrar_mercado`, que ja carrega antes: fundir la faria a fusao acontecer duas vezes e tornaria invisivel, para quem le `main()`, que existe uma leitura de disco.
- **Captura ampla no `carregar`, com aviso alto.** Nao propagar e a rota de recuperacao do usuario; nao calar e o que impede o defeito original de voltar com uma camada por cima.
- **`calibrar_tiat` e `--solo` nao foram tocados.** Os dois ja fazem load-mutate-save. O caso 6 os prende por fora, sem alterar uma linha deles.
- **O `--tiat` ficou sem caso por CUSTO.** Ele e alcancavel pelo mesmo idioma do caso 6 mais tres monkeypatches (`_selecionar_regiao` duas vezes, `_gravar_conferencia`). O que dispensa o caso e que `calibrar_tiat` ja e load-mutate-save comprovado por leitura: seria guarda de regressao, e nao prova de conserto. Escrito na docstring do modulo de teste.

## Deviations from Plan

Nenhuma — o plano foi executado exatamente como escrito.

Duas armadilhas que o plano ja tinha desarmado e que se confirmaram na execucao:

1. **O caso 3 passou no RED**, como o plano previu, e nao foi alterado. Ele e guarda de regressao contra um load-mutate-save ingenuo que faria `nomes`/`assinaturas`/`hp_proprio` velhos sobreviverem a uma recalibracao — assinatura estale contra geometria nova manda a party socorrer a pessoa errada.
2. **O semeador passou pelo `Calibracao.carregar` de primeira**, porque a grade foi semeada primeiro e as quatro colunas derivadas de dentro dela (`_conferir_uma_coluna` exige `dx >= grade.dx` e `dx + largura <= grade.dx + grade.largura`), os moldes levaram `bytes` em hex de comprimento `altura * largura`, e todo `mercado_limiar_*` ficou em `(0, 1]`. A linha `Calibracao.carregar(alvo)` dentro do `_semear` ficou no arquivo como guarda permanente.

## Issues Encountered

- **`tests/test_agenda.py` abortou a primeira rodada da suite completa** com `KeyboardInterrupt` aos 87 testes — o flake conhecido, registrado no plano. Abortar nao e falhar: a segunda rodada fechou limpa. Uma repeticao, nao tres.

## Verificacao

| Portao | Resultado |
|---|---|
| Suite completa | **1830 passed, 2 skipped** — baseline 1824 + os 6 casos novos, nenhuma falha nova |
| Digest do `calibration.json` real | `ac09844e…ebea1a` **antes E depois**, valor NAO-VAZIO nas duas pontas → `CALIBRATION.JSON INTOCADO` |
| `git status --porcelain calibration.json` | vazio |
| `grep -cE '^ +cal\.salvar\(ARQUIVO_CALIBRACAO\)$'` | **3** — os tres pontos de gravacao seguem existindo, nenhum duplicado ou removido |
| `VERSAO_DO_ESQUEMA` no diff | **0 ocorrencias** — nenhum bump |
| `git diff --name-only` | so `l2scanner/calibrar.py` e `tests/test_calibrar_nao_apaga_mercado.py`; `rastreador.py` e `visao.py` intactos |
| `tests/test_firewall_escopo.py` (FIRE-01) | 18 passed — nenhuma dependencia nova |
| Contagem de campos | `OK 27 campos preservados` |
| Delecoes nos commits | nenhuma, nos tres |

Medicao extra que o plano pediu e que confirma a honestidade do caso 6: rodado contra o `calibrar.py` do commit `93a9676` (anterior ao conserto), `TestOModoSoloContinuaPreservando` deu **1 passed**. Ele passa por DESENHO — `--solo` ja preservava —, e nao por acidente. Ele prova a invariante, nao o conserto.

## Known Stubs

Nenhum. Nenhum valor vazio, placeholder ou TODO foi introduzido.

## User Setup Required

Nenhum — nenhuma configuracao de servico externo.

## Pendente: o `<human-check>` e a JANELA 13

**A JANELA 13 foi deixada ABERTA na `STATE.md` do workstream mercado, de proposito.** O plano condiciona o fechamento a uma conferencia que nenhum teste substitui, porque so a maquina do usuario tem os 13 moldes de verdade:

1. **COPIAR o `calibration.json` real para um nome de rascunho — a copia de seguranca vem PRIMEIRO.** O plano ja custou os moldes uma vez.
2. Rodar `python -m l2scanner.calibrar --auto` (ou o `calibrar.bat` normal, ja com a copia ao lado).
3. Confirmar que `mercado_templates_de_digito` continua com **13 entradas** depois da rodada.

Passando, fechar a JANELA 13 citando o commit `0c9038c`.

## Self-Check: PASSED

- `tests/test_calibrar_nao_apaga_mercado.py` existe em disco.
- `l2scanner/calibrar.py` existe e contem `CAMPOS_DA_PARTY` (2 ocorrencias) e `fundir_com_a_calibracao_em_disco` (2 ocorrencias: a definicao e a unica chamada).
- Os tres commits existem: `93a9676`, `0c9038c`, `6f723ef`.
- Todos os `<acceptance_criteria>` das tres tasks foram re-executados e passaram; a tabela de verificacao acima e a saida deles.

---
*Quick task: 260830-apd*
*Completed: 2026-08-30*
