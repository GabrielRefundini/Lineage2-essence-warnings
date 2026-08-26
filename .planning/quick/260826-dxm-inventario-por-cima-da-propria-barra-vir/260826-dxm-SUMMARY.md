---
phase: quick-260826-dxm
plan: 01
subsystem: detection
tags: [opencv, visao, barra-propria, falso-positivo, moldura, regressao]

requires:
  - phase: 2
    provides: "medir_barra, limiares HSV calibrados, e a observacao de que a parte vazia da barra e transparente e mostra o terreno"
  - phase: 3
    provides: "o rastreador que converte hp_proprio == 0.0 em MORREU, e None em CONGELA"
provides:
  - "Segundo portao em `barra_propria_legivel`: moldura escura = recorte coberto por outra janela do jogo"
  - "`_moldura_da_barra_propria` — menor media de cinza entre as quatro bordas do recorte"
  - "`BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0`, com a medicao registrada ao lado"
  - "9 fixtures reais da barra propria versionadas (as 8 antigas estavam so no disco)"
  - "22 testes novos prendendo os DOIS sentidos: o inventario nao vira morte, a morte de verdade continua saindo"
affects: [modo-solo, rastreador, calibracao-da-barra-propria]

actuals:
  tokens: 9900
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Dois portoes EM SERIE no mesmo discriminador, cada um cobrindo um modo de falha que o outro comprovadamente nao pega"
    - "Polaridade do sinal documentada na docstring quando ela e o inverso de um irmao no mesmo arquivo"

key-files:
  created:
    - tests/test_inventario_por_cima_da_barra_propria.py
    - tests/fixtures/barra_propria/quase_vazia_terreno_atras.png
    - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
  modified:
    - l2scanner/visao.py

key-decisions:
  - "O discriminador do recorte coberto e a MOLDURA, nao o contraste — e isso esta medido, nao suposto: coberta_0 da desvio 36.54, MAIOR que os 35.47 de livre_0. Nao existe limiar de desvio que separe."
  - "Limiar 60.0, no PE da faixa medida e nao no meio do vao (63.8). Errar para baixo aqui suprimiria morte real, que e o pior desfecho declarado do projeto."
  - "A MENOR das quatro bordas, nunca a media: o inventario cobre um lado so, e a media diluiria justamente o lado coberto."
  - "POLARIDADE INVERTIDA em relacao a `_bordas_da_barra_intactas`, escrita na docstring — a party rejeita borda CLARA demais (olha o chrome escuro de FORA da barra), a propria rejeita moldura ESCURA demais (as quatro bordas caem DENTRO do campo da barra)."
  - "O proxy de barra vazia e a barra de MP, nao uma sintese: nenhuma amostra alinhada de HP proprio em nivel baixo existe no repositorio."

patterns-established:
  - "Tripwire de medicao: um teste que afirma ao mesmo tempo que o portao antigo aprovaria o caso e que o portao completo o rejeita — impede que alguem apague o portao novo por acha-lo redundante"
  - "Verificacao por MUTACAO antes de fechar a tarefa: apagar cada portao e apertar o limiar, e conferir que a suite quebra dizendo o que quebrou"

requirements-completed: [QUICK-260826-dxm]

coverage:
  - id: D1
    description: "Um recorte da barra propria coberto pelo inventario e declarado ILEGIVEL — as quatro fixtures reais coberta_0..3"
    requirement: "QUICK-260826-dxm"
    verification:
      - kind: unit
        ref: "tests/test_inventario_por_cima_da_barra_propria.py::TestAsOitoFixturesReaisNosDoisSentidos::test_coberta_pelo_inventario_e_ILEGIVEL"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uma barra propria LIVRE continua LEGIVEL — livre_0..3 e as quatro *__hp_proprio*.png que test_modo_solo.py ja globa"
    requirement: "QUICK-260826-dxm"
    verification:
      - kind: unit
        ref: "tests/test_inventario_por_cima_da_barra_propria.py::TestAsOitoFixturesReaisNosDoisSentidos::test_livre_e_LEGIVEL"
        status: pass
      - kind: unit
        ref: "tests/test_modo_solo.py::TestBarraIlegivelNaoVIRAMorte::test_a_barra_real_do_usuario_e_legivel"
        status: pass
    human_judgment: false
  - id: D3
    description: "O caminho do defeito deixou de existir de ponta a ponta: extrair devolve hp_proprio None (nunca 0.0) e 30 observacoes nao emitem morte"
    requirement: "QUICK-260826-dxm"
    verification:
      - kind: integration
        ref: "tests/test_inventario_por_cima_da_barra_propria.py::TestOInventarioNaoViraMorte"
        status: pass
    human_judgment: false
  - id: D4
    description: "RESTRICAO DURA — a morte de verdade continua saindo: barra real quase vazia atravessa o portao, chega como 0.0 e o rastreador emite MORREU"
    requirement: "QUICK-260826-dxm"
    verification:
      - kind: integration
        ref: "tests/test_inventario_por_cima_da_barra_propria.py::TestAMorteDeVerdadeContinuaSaindo"
        status: pass
    human_judgment: false
  - id: D5
    description: "O risco de terreno escuro registrado como pendencia, com a direcao do dano nomeada"
    verification: []
    human_judgment: true
    rationale: "Fechar a pendencia exige uma gravacao da propria barra com HP baixo em ambiente escuro — o repositorio nao tem essa amostra e nenhum teste pode inventa-la"

duration: 26min
completed: 2026-08-26
status: complete
---

# Quick 260826-dxm: o inventário por cima da própria barra virava morte — Summary

**O portão da barra própria ganhou um segundo teste, de MOLDURA, e com isso o falso positivo mais volumoso do projeto (27 mortes + 27 ressurreições falsas num único `scanner.log`) deixou de existir — sem tirar nada do caminho da morte de verdade, que agora tem teste próprio contra um recorte real de barra praticamente vazia.**

## Performance

- **Duração:** ~26 min
- **Tarefas:** 2 de 2
- **Arquivos modificados:** 12 (1 de código, 1 de teste, 9 fixtures, 1 pendência)
- **Testes:** 758 passando + 2 skipped → **780 passando + 2 skipped** (22 novos, zero mudanças de veredito nos antigos)

## Accomplishments

- **O defeito foi fechado na raiz e provado de ponta a ponta.** `extrair` sobre um frame cujo `extras['hp_proprio']` é uma fixture coberta agora devolve `Observacao.hp_proprio is None` — nunca `0.0` — e essa observação alimentada 30 vezes no rastreador em modo solo emite **zero** evento de morte. Antes, a segunda leitura já disparava `MORREU` (medido: evento às 102 no vermelho da TDD).
- **A restrição dura ganhou teste próprio, e ele estava VERDE antes da implementação.** Um recorte real de barra praticamente vazia atravessa o portão novo, chega em `extrair` como `hp_proprio == 0.0` e o rastreador emite `MORREU` com o nome certo. O remédio não transformou o scanner num que cala.
- **O discriminador foi escolhido por medição, não por intuição.** O desvio-padrão parecia bastar e comprovadamente não basta: `coberta_0` dá **36.54**, MAIOR que os **35.47** de `livre_0`. A moldura separa limpo — pior coberta 48.92, pior livre/vazia 78.73, vão de 29.8 pontos.
- **As 8 fixtures irmãs entraram no git.** Elas existiam no disco e **nunca tinham sido commitadas** (ver Deviations): um clone novo perdia a bateria inteira.
- **Os dois portões e o limiar foram conferidos por MUTAÇÃO**, no estilo que o repositório já usa: apagar o desvio, apagar a moldura e apertar o limiar para 90 quebram a suíte, cada um dizendo o que quebrou.

## Task Commits

1. **Task 1 (tracer, TDD RED): a fixture e o caminho inteiro nos dois sentidos** — `ed01df5` (test)
2. **Task 1 (TDD GREEN): o portão de moldura** — `1fd3db5` (fix)
3. **Task 2: a bateria das 8 fixtures e o tripwire do desvio** — `bed248d` (test)
4. **Task 2: a pendência do terreno escuro** — `5e7c139` (docs)

## Files Created/Modified

- `l2scanner/visao.py` — `BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0` (com a medição no comentário), `_moldura_da_barra_propria`, e o segundo portão EM SÉRIE dentro de `barra_propria_legivel`
- `tests/test_inventario_por_cima_da_barra_propria.py` — 22 testes: o caminho de ponta a ponta nos dois sentidos, as 8 fixtures reais, o proxy de barra vazia e o tripwire do desvio-padrão
- `tests/fixtures/barra_propria/quase_vazia_terreno_atras.png` — recorte 191x24 de `recordings/agora_janela.png[741:765, 294:485]`: a barra de **MP** do próprio personagem a 170/2567 (6.6%), o único proxy alinhado de barra vazia do repositório
- `tests/fixtures/barra_propria/{coberta,livre}_0..3.png` — as 8 fixtures reais, agora **versionadas**
- `.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md` — a pendência com a direção do dano nomeada

## Medições registradas

| recorte 191x24 | moldura_min | desvio | `medir_barra` (HP) |
|---|---|---|---|
| `coberta_0.png` | **48.00** | 36.54 | 0.87 |
| `coberta_1.png` | **48.92** | 29.66 | 0.00 |
| `coberta_2.png` | **28.00** | 24.55 | 0.00 |
| `coberta_3.png` | **29.00** | 19.58 | 0.00 |
| `livre_0..3.png` | **86.42** | 35.18–35.47 | 1.00 |
| as 4 `*__hp_proprio*.png` | **86.42** | 38.63 | 1.00 |
| `quase_vazia_terreno_atras.png` | **78.73** | 31.71 | **0.00** |
| `np.full((8,120,3), 60)` | 60.00 | 0.00 | — |
| ruído `rng(7)` | 120.33 | 73.20 | — |

Todas conferidas na execução contra os pixels reais; batem com a tabela do plano dígito a dígito.

## Decisions Made

- **A MENOR das quatro bordas, não a média.** O inventário cobre um lado só da barra (`coberta_1`: col0 48.92 mas col-1 74.54); uma média das quatro diluiria justamente o lado coberto e deixaria a fixture passar.
- **Limiar no pé da faixa (60), não no meio do vão (63.8).** A assimetria é deliberada: errar para cima produz alarme falso (barulhento, autocorrigível), errar para baixo produz silêncio numa morte real (o pior desfecho declarado do projeto).
- **A armadilha do `np.full(60)` virou teste em vez de virar surpresa.** Esse recorte, que `test_modo_solo.py` afirma ILEGÍVEL desde o modo solo, dá moldura **exatamente 60.00** e passa no portão novo — ele só continua rejeitado porque o de desvio não saiu do lugar. É o motivo concreto de D-01 (os dois EM SÉRIE) existir, e está travado com mensagem de falha que diz isso.
- **A polaridade invertida foi escrita na docstring.** Sem essa frase o próximo leitor "conserta" o sinal por analogia com `_bordas_da_barra_intactas` e reabre o defeito.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] As 8 fixtures da barra própria nunca tinham sido commitadas**

- **Encontrado durante:** Task 1, no `git status` antes do commit
- **Problema:** O plano supõe, no registro de ameaças (T-260826-02), que "as 8 fixtures irmãs já estão no repositório pelo mesmo critério". Elas estão no **disco**, e `git ls-files tests/fixtures/barra_propria/` devolvia **vazio** — nenhuma delas tem histórico. Não é `.gitignore` (a regra `!tests/fixtures/**/*.png` as libera, e `git check-ignore` confirma que não estão ignoradas): elas simplesmente nunca foram adicionadas. Um clone novo perderia a bateria de regressão inteira da Task 2, e os testes falhariam com "fixture não pode ser lida".
- **Correção:** as 9 PNGs (as 8 antigas + a nova) foram adicionadas explicitamente, uma a uma, no commit `ed01df5`.
- **Verificação:** `git ls-files tests/fixtures/barra_propria/` lista as nove.

**2. [Rule 2 - Faltava] Mensagem de falha própria para o lado da mutação C**

- **Encontrado durante:** Task 2, na conferência por mutação
- **Problema:** `test_o_portao_de_desvio_continua_no_lugar` afirma que a moldura de `np.full(60)` é `>= BRILHO_MINIMO_DA_MOLDURA_PROPRIA`. Se alguém subir o limiar acima de 60, essa asserção quebra — e a mensagem original culpava o portão de desvio, que não teria nada a ver.
- **Correção:** mensagem própria na asserção, dizendo que a armadilha deixou de existir e que a medição precisa ser revista antes de mexer no portão de desvio.
- **Committed em:** `bed248d`

---

**Total de desvios:** 2 auto-corrigidos (1× Rule 3, 1× Rule 2)
**Impacto no plano:** nenhum desvio de escopo. O primeiro é pré-requisito de corretude — sem ele, a entrega da Task 2 não sobreviveria a um clone.

## Issues Encountered

Nenhum. As medições do plano (moldura, desvio e `medir_barra` das nove fixtures, mais as duas armadilhas) foram todas reproduzidas na execução e bateram com a tabela planejada, incluindo o `moldura_min == 78.73` exigido da fixture nova.

## Verificação por mutação

| Mutação | O que quebrou |
|---|---|
| portão de desvio apagado | `test_o_portao_de_desvio_continua_no_lugar` + `test_modo_solo.py::test_a_visao_devolve_None_para_recorte_degenerado` (2 falhas) |
| portão de moldura apagado | 13 falhas, incluindo as 4 cobertas e o tripwire |
| limiar apertado para 90 | 8 falhas, incluindo `test_a_barra_quase_vazia_real_e_LEGIVEL` — a direção do dano fica exposta |

## Known Stubs

Nenhum.

## Pendência aberta (D-04)

`.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md`, severidade **major**.

O portão supõe que a parte vazia da barra mostra terreno mais claro que 60. Medido **78.73**, mas **sobre grama à luz do dia** — folga real de 18.73 pontos. Em masmorra escura ou à noite o terreno atrás da parte vazia pode cair abaixo do limiar e uma barra vazia **de verdade** seria declarada ilegível: `hp_proprio = None`, o rastreador congela, e **morte real não é anunciada**. Fecha com uma gravação da própria barra com HP baixo em ambiente escuro (critério de aceite: moldura > 70), que hoje o repositório não tem.

A troca é assimétrica e conhecida: o defeito corrigido era **constante** (27 ocorrências num único log), o risco aberto é **condicional** e nunca foi observado.

## Verification Results

1. `python -m pytest -q` → **780 passed, 2 skipped**. Baseline era 758 + 2; os 22 novos são exatamente os deste plano, e nenhum teste antigo mudou de veredito.
2. `python -m pytest tests/test_inventario_por_cima_da_barra_propria.py tests/test_modo_solo.py -q` (verify da Task 1) → 25 passed.
3. `git status --short` → limpo, e `tests/fixtures/barra_propria/quase_vazia_terreno_atras.png` está **rastreada**.
4. Diff de `l2scanner/visao.py`: o portão de desvio continua lá, o de moldura foi acrescentado EM SÉRIE (`and`), e a constante carrega a medição no comentário.

## Self-Check: PASSED
