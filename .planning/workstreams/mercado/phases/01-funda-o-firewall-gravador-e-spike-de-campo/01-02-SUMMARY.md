---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 02
subsystem: testing
tags: [spike, roteiro, template-matching, matchTemplate, calibracao, fixtures, opencv]

requires:
  - phase: 01-01
    provides: "--record-janela (gravacao da JANELA COMPLETA) e o gravador que so conta escrita confirmada"
provides:
  - "ROTEIRO-SPIKE.md: pre-voo + 8 cenarios rotulados, com comando copiavel, duracao e instrucao de tela"
  - "tools/conferir_gravacoes_do_spike.py: portao executavel com 5 conferencias, todas com prova de vermelho"
  - "l2scanner/mercado_visao.py: casamento_da_ancora, mercado_aberto, molde_para_hex/molde_de_hex, CASAMENTO_MINIMO_DA_ANCORA=0.73 MEDIDO"
  - "4 chaves opcionais de mercado em calibration.json, VERSAO_DO_ESQUEMA congelada em 2"
  - "tests/fixtures/mercado/: 13 recortes resgatados do incidente 27x (1 molde, 2 positivos, 10 negativos)"
  - "RESPOSTA MEDIDA da pergunta em aberto A1: o painel do mercado ANDA — ancora em retangulo fixo nao o encontra"
affects: [01-03 respostas do spike, 01-04 calibracao e deteccao de mercado, fase 2 estabilizador de pagina, fase 4 consumidor de oclusao]

actuals:
  tokens: 41800
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Ancora POSITIVA propria em modulo puro separado, nunca estendendo o gate de brilho da barra propria"
    - "Negativo ADVERSARIAL: cortado na posicao de melhor casamento do frame, nao num pedaco de terreno qualquer"
    - "Limiar no MEIO da margem medida, com pior positivo / melhor negativo / margem escritos ao lado da constante"
    - "Portao de checkpoint executavel: o que e verificavel por programa nao fica em prosa"
    - "Fixture resgatada + pytest.skip com a razao dita para o que so existe em recordings/"

key-files:
  created:
    - .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/ROTEIRO-SPIKE.md
    - tools/conferir_gravacoes_do_spike.py
    - l2scanner/mercado_visao.py
    - tests/test_mercado_ancora.py
    - tests/test_calibracao_mercado.py
    - tests/fixtures/mercado/ (13 PNGs)
  modified:
    - l2scanner/calibracao.py

key-decisions:
  - "A ancora e a faixa de TITULO do painel (912, 350, 100x28 no f000), nao a linha de cabecalhos de coluna: tooltip e marcacao de alvo caem sobre as LINHAS"
  - "Limiar 0.73, no meio da margem medida 0.4624..0.9996 — nao chutado"
  - "Negativos cortados na posicao ADVERSARIAL (melhor casamento do frame), que e o numero que um consumidor com busca precisa vencer"
  - "casamento_da_ancora aceita BGR e converte: comparar 3 canais com 1 canal devolve numero errado calado"
  - "molde_de_hex confere dimensoes declaradas contra o tamanho real dos bytes antes do reshape"
  - "O molde fica em calibracao.py como dict CRU, sem decodificar — senao calibracao.py passaria a importar numpy para ler configuracao"

patterns-established:
  - "Medir antes de o usuario gastar o recurso escasso: o de-risking mudou o roteiro DUAS vezes antes do gate"
  - "Quando a medicao desmente a pesquisa, a medicao vence e a correcao vai para o topo do teste"

requirements-completed: []

coverage:
  - id: D1
    description: "ROTEIRO-SPIKE.md: pre-voo + 8 cenarios, cada um com comando copiavel, duracao alvo e instrucao de tela"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "python -c ... verifica os 9 rotulos presentes no ROTEIRO-SPIKE.md"
        status: pass
    human_judgment: true
    rationale: "A automacao prova que os 9 rotulos estao no arquivo; ela nao prova que o texto e SEGUIVEL sem perguntar nada, que e o criterio de pronto da task. So um humano lendo de cima a baixo responde isso — e o leitor alvo e o usuario, que vai executa-lo no segundo monitor."
  - id: D2
    description: "Portao executavel das gravacoes: 5 conferencias (sufixos, JSONL nao vazio, zero orfaos, JSONL == PNGs no disco, dimensao de JANELA)"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "python tools/conferir_gravacoes_do_spike.py (sem gravacoes) -> exit 1 nomeando os 8 sufixos ausentes"
        status: pass
      - kind: other
        ref: "pasta fabricada com PNG na dimensao do recorte da party -> exit 1 nomeando o modo errado"
        status: pass
      - kind: other
        ref: "JSONL citando arquivo inexistente -> exit 1 nomeando o orfao"
        status: pass
      - kind: other
        ref: "PNG no disco sem linha no JSONL -> exit 1 com a contagem divergente"
        status: pass
      - kind: other
        ref: "8 pastas validas fabricadas -> exit 0 com a tabela"
        status: pass
    human_judgment: false
  - id: D3
    description: "casamento_da_ancora separa painel aberto de painel fechado com margem 0.5372 sobre a gravacao real do incidente 27x"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_com_o_painel_aberto_o_casamento_passa_do_limiar (2 casos)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_sem_o_painel_o_casamento_fica_abaixo_do_limiar (10 casos)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_a_margem_medida_continua_grande"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_o_banner_com_AS_MESMAS_PALAVRAS_nao_engana"
        status: pass
    human_judgment: false
  - id: D4
    description: "Entrada degenerada (vazio, uniforme, molde maior que o alvo) devolve 0.0 e nunca vira mercado aberto"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_ancora.py#TestOsDegeneradosFalhamFECHADO (6 testes)"
        status: pass
    human_judgment: false
  - id: D5
    description: "As 4 chaves de mercado entram no calibration.json sem subir a VERSAO_DO_ESQUEMA e sem migracao"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_calibracao_mercado.py#TestACalibracaoAntigaContinuaValendo (4 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_calibracao_mercado.py#TestORoundTripDasChavesNovas (4 testes)"
        status: pass
    human_judgment: false
  - id: D6
    description: "O painel do mercado ANDA — resposta medida da pergunta em aberto A1"
    requirement: "DETC-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_o_f005_prova_que_o_painel_ANDA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_ancora.py#test_o_positivo_f005_veio_da_posicao_DESLOCADA (pula sem recordings/)"
        status: pass
    human_judgment: false
  - id: D7
    description: "As 8 sessoes reais do World Exchange gravadas pelo usuario"
    requirement: "FUND-02"
    verification: []
    human_judgment: true
    rationale: "PORTAO EXTERNO NAO CUMPRIDO. Exige a conta, o cliente e o servidor do usuario — nao ha caminho de automacao. E o motivo declarado de este plano parar aqui."

duration: ~50 min
completed: 2026-08-27
status: halted
---

# Phase 1 Plan 2: Roteiro do spike e a ancora do mercado, MEDIDA — Summary

**O roteiro das 8 gravações está pronto com um portão executável que o confere, e a técnica da âncora do painel foi medida contra a gravação do próprio incidente 27x — com margem de 0,5372 e uma descoberta que muda o desenho: o painel do mercado ANDA. O plano para aqui, no portão externo: só o usuário pode gravar as sessões.**

## ESTADO: PARADO NO PORTÃO EXTERNO (por desenho, não por falha)

| Task | O que é | Estado |
|---|---|---|
| 1 | `ROTEIRO-SPIKE.md` + `tools/conferir_gravacoes_do_spike.py` | **COMPLETA**, commitada |
| 2 | Trilho da âncora medido + chaves de calibração | **COMPLETA**, commitada |
| 3 | O usuário grava as 8 sessões do World Exchange | **ABERTA — `gate="blocking-human"`** |

A Task 3 é um `checkpoint:human-action` com `gate="blocking-human"`. Ela não foi executada,
não foi simulada e não foi contornada: as gravações exigem a conta, o cliente e o servidor do
usuário. O `status: halted` no frontmatter é deliberado — qualquer plano que dependa deste fica
bloqueado até as gravações existirem e passarem no portão.

## Performance

- **Duration:** ~50 min
- **Tasks:** 2 de 3 (a terceira é o portão externo)
- **Files created/modified:** 19 (18 criados, 1 alterado)
- **Suíte:** 1213 passed, 6 skipped (baseline do worktree sem as duas suítes novas: 1179/4 — **+34 passando, zero regressões**)

## Accomplishments

- **O roteiro existe e tem um portão com dentes.** O `ROTEIRO-SPIKE.md` tem pré-voo obrigatório
  e 8 cenários, cada um com comando copiável, duração alvo e instrução de tela. Ao lado dele,
  `tools/conferir_gravacoes_do_spike.py` faz cinco conferências por pasta — e as cinco têm prova
  de vermelho registrada (ver a tabela de deviations e a coverage D2). O sinal de alarme mais
  caro (PNG de ~170 KB no lugar de ~3,5 MB) deixou de depender do olho do usuário.
- **A âncora do painel está medida, não chutada.** Margem de **0,5372** entre o pior positivo
  (0,9996) e o melhor negativo (0,4624), com o limiar em **0,73**, no meio. Sem zona cinzenta:
  os 10 negativos ficam entre 0,3253 e 0,4624; os 2 positivos acima de 0,9996.
- **A pergunta aberta A1 foi respondida antes de custar caro: o painel ANDA.** Isso derruba a
  suposição em que a arquitetura da detecção ia se apoiar (retângulo fixo calibrado) e foi
  descoberto com material que já estava no disco — não com uma das 8 sessões do usuário.
- **O roteiro mudou por causa da medição, que é exatamente para isso que o de-risking existe.**
  Duas edições, ambas antes do gate: o bloco "arraste o painel" virou três posições + fecha-reabre
  (não faz mais sentido perguntar *se* ele arrasta), e o cenário `mercado-fechado` ganhou o pedido
  do banner de sistema — o negativo mais difícil que temos.
- **`l2scanner/visao.py` e `l2scanner/rastreador.py` não têm uma linha alterada.** A proibição mais
  cara do projeto continua intacta, conferida no diff.

## A TABELA DE SCORES MEDIDOS

Molde: `tests/fixtures/mercado/molde_da_ancora.png`, 100×28 em tons de cinza, cortado da faixa
de título "XM Market" de `recordings/inv3/f000_JANELA.png` (1720×1392) no retângulo
**`esquerda=912, topo=350, largura=100, altura=28`**.

### Positivos — painel do mercado ABERTO

| Fixture | Score | Cortado em | Observação |
|---|---:|---|---|
| `ancora_27x_f000` | **1.0000** | (912, 350) | é o frame de onde o molde saiu |
| `ancora_27x_f005` | **0.9996** | (731, 493) | **mesma arte, 181 px à esquerda e 143 px abaixo** |

### Negativos — painel do mercado FECHADO

Cada um cortado na posição de **melhor casamento do seu frame inteiro** — o corte adversarial,
o ponto mais parecido com a faixa de título naquele frame.

| Fixture | Score | Cortado em | O que é |
|---|---:|---|---|
| `negativo_escuro` | **0.4624** | (938, 180) | banner de sistema "Someone has registered an item on XM Market!" |
| `negativo_f025` | 0.4114 | (168, 1044) | inventário aberto |
| `negativo_f040` | 0.4102 | (168, 930) | inventário aberto |
| `negativo_agora` | 0.4075 | (168, 961) | jogo normal |
| `negativo_f010` | 0.4053 | (104, 1143) | inventário aberto |
| `negativo_f015` | 0.4051 | (104, 1143) | inventário aberto |
| `negativo_f030` | 0.3903 | (168, 1013) | inventário aberto |
| `negativo_f020` | 0.3614 | (423, 1143) | inventário aberto |
| `negativo_base` | 0.3506 | (94, 930) | jogo normal |
| `negativo_f035` | 0.3253 | (94, 1044) | inventário aberto |

### A margem

```
pior POSITIVO    0.9996
melhor NEGATIVO  0.4624
MARGEM           0.5372
LIMIAR           0.73     <- CASAMENTO_MINIMO_DA_ANCORA, no meio da margem
```

**O negativo mais caro merece nota.** `negativo_escuro` é o aviso de sistema
*"Someone has registered an item on XM Market!"* no log do jogo: as **mesmas palavras na tela,
com o painel fechado**. Um detector que procurasse o *texto* "XM Market" dispararia ali. A
âncora casa a *arte* do painel e lê 0,4624 — a 0,27 do limiar.

## Arquivos resgatados para `tests/fixtures/mercado/`

13 PNGs, todos **100×28 em tons de cinza** (~1,8 a 2,5 KB cada):

| Arquivo | Origem |
|---|---|
| `molde_da_ancora.png` | `recordings/inv3/f000_JANELA.png` @ (912, 350) |
| `ancora_27x_f000.png` | `recordings/inv3/f000_JANELA.png` @ (912, 350) |
| `ancora_27x_f005.png` | `recordings/inv3/f005_JANELA.png` @ (731, 493) |
| `negativo_f010.png` … `negativo_f040.png` (7) | `recordings/inv3/f0NN_JANELA.png`, cada um na sua posição adversarial |
| `negativo_base.png` | `recordings/base_janela.png` @ (94, 930) |
| `negativo_agora.png` | `recordings/agora_janela.png` @ (168, 961) |
| `negativo_escuro.png` | `recordings/escuro_janela.png` @ (938, 180) |

**Descartados, com a razão (T-02-01 e A4):**

- `recordings/inventario/` (30 PNGs) e `recordings/inv2/` (90 PNGs) — **zero frames `_JANELA`**.
  Só têm recortes da party window, que não contêm o painel. A pesquisa esperava usá-los como
  "o negativo mais valioso"; o material não existe nesse formato. Compensado de sobra: 7 dos 10
  negativos acabaram sendo frames de inventário do próprio `inv3`.
- `recordings/hp_baixo/` — sem PNGs.

**Privacidade (T-02-01), auditável:** os 13 recortes são a faixa de título do painel, 100×28,
sem nome de personagem e sem mensagem de jogador. O único texto legível em qualquer um deles é
o do `negativo_escuro`, um banner de **sistema** que diz literalmente *"Someone"*. `recordings/`
continua gitignored e local.

## Task Commits

1. **Task 1: roteiro + portão executável** — `2fb8187` (feat)
2. **Task 2 (RED): provas da âncora e das chaves + fixtures resgatadas** — `cbfee55` (test)
3. **Task 2 (GREEN): `mercado_visao` com o limiar medido + chaves na calibração** — `50e68cd` (feat)
4. **Task 2 (consequência): roteiro atualizado pelo que a medição descobriu** — `fb3aad8` (docs)

## Files Created/Modified

- `.planning/.../ROTEIRO-SPIKE.md` — checklist do usuário: pré-voo + 8 cenários, custo de disco
  medido, 7 perguntas de campo, pedido do item encantado, notas de escopo e privacidade
- `tools/conferir_gravacoes_do_spike.py` — portão do checkpoint, 5 conferências, `--pasta-base` e
  `--calibracao` para ser testável fora de `recordings/`
- `l2scanner/mercado_visao.py` — módulo puro: `casamento_da_ancora`, `mercado_aberto`,
  `molde_para_hex`/`molde_de_hex`, `CASAMENTO_MINIMO_DA_ANCORA = 0.73`
- `l2scanner/calibracao.py` — 4 campos opcionais (`mercado_ancora`, `mercado_molde_da_ancora`,
  `mercado_limiar_da_ancora`, `mercado_geometria_da_captura`) pelos três pontos do trilho
  `banner_manutencao`; `VERSAO_DO_ESQUEMA` intocada em 2
- `tests/test_mercado_ancora.py` (298 linhas) — 24 testes: positivos, negativos, degenerados,
  empacotamento, fidelidade das fixtures à gravação
- `tests/test_calibracao_mercado.py` (127 linhas) — 9 testes: compatibilidade, round-trip, recusa
  de versão
- `tests/fixtures/mercado/` — 13 recortes resgatados

## Decisions Made

- **A âncora é a faixa de TÍTULO, não a linha de cabeçalhos de coluna.** As duas estão sempre
  presentes com o painel aberto, mas tooltip e marcação de alvo caem sobre as **linhas** — e
  esses são dois dos cenários que o usuário vai gravar. O título é arte opaca do painel.
- **Limiar no meio da margem, com os três números ao lado da constante.** 0,73 não é um número
  bonito escolhido a dedo: é `(0.9996 + 0.4624) / 2`.
- **Negativos cortados na posição adversarial.** Cortar o mesmo retângulo fixo em frames sem
  painel dava scores de ~-0,02 — verdadeiros e inúteis, porque medem terreno. O número que
  importa é o do ponto mais parecido de cada frame, porque é ele que um consumidor com busca
  precisa vencer.
- **`casamento_da_ancora` aceita BGR e converte.** O consumidor da Fase 4 recebe BGR da captura.
  Comparar 3 canais com um molde de 1 canal não levanta erro — devolve um número errado calado,
  que é o modo de falha que esta fase existe para eliminar.
- **O molde mora em `calibracao.py` como dict cru.** Decodificar ali obrigaria um módulo de
  configuração a importar numpy. Quem decodifica é `mercado_visao.molde_de_hex`, que já valida.

## Deviations from Plan

### 1. [Rule 1 - Bug na premissa] A pesquisa dizia que os 9 frames `_JANELA` tinham o painel. Só 2 têm.

- **Found during:** Task 2, na primeira medição
- **Issue:** A primeira rodada mediu o retângulo fixo do `f000` em todos os 9 frames e só o
  `f000` casou (1.0000); os outros 8 deram ~-0,02 — o mesmo que os negativos. A `01-RESEARCH.md`
  (Descoberta 3) afirma "10 frames de janela completa ... painel de mercado aberto ao centro",
  e o plano construiu o critério de aceite "pelo menos 8 positivos do 27x" em cima disso.
- **Investigação:** busca do molde na janela inteira de cada frame, que separa "andou" de
  "fechou". Resultado: `f000` 1.0000 @ (912,350), `f005` 0.9996 @ (731,493), e `f010`–`f040`
  entre 0,32 e 0,41 em qualquer posição. Inspeção visual do `f020_JANELA.png` confirma: o painel
  aberto ali é o **INVENTÁRIO**, não o mercado. A pasta se chama `inv3` justamente por isso.
- **Fix:** classificação medida em vez de assumida. 2 positivos reais, 10 negativos reais.
- **Consequência no critério de aceite:** *"`tests/fixtures/mercado/` contém ... pelo menos 8
  positivos do 27x"* **NÃO É SATISFEITO E NÃO PODE SER**: só existem 2 frames com o painel. As
  alternativas seriam fabricar positivos sintéticos (recortes deslocados do mesmo frame), o que
  inflaria a contagem sem acrescentar uma única evidência nova. O critério irmão — "pelo menos 2
  negativos" — foi superado 5×.
- **Files:** `tests/fixtures/mercado/`, `tests/test_mercado_ancora.py`
- **Verification:** `test_o_f005_prova_que_o_painel_ANDA`, mais os 10 negativos parametrizados
- **Committed in:** `cbfee55`

### 2. [Rule 2 - Missing Critical] O painel ANDA — e nada no plano previa isso

- **Found during:** Task 2, na investigação acima
- **Issue:** `f005` casa 0,9996 num ponto **181 px à esquerda e 143 px abaixo** de `f000`. A
  suposição A1 da pesquisa ("o painel abre em posição FIXA; âncora em retângulo calibrado
  basta") é **falsa, medida**. Um `mercado_ancora` fixo no `calibration.json` não encontraria o
  painel numa segunda posição — e falharia **calado**, que é o pior modo.
- **Fix:** três coisas, nenhuma delas mudando o contrato do módulo. (a) A descoberta está escrita
  no topo de `mercado_visao.py`, com os números e a instrução ao consumidor: **localizar antes de
  comparar**. (b) O campo `mercado_ancora` em `calibracao.py` carrega o aviso de que é a posição
  de *referência* de onde o molde saiu, não a promessa de onde o painel estará. (c) Um teste
  prende a coordenada deslocada, para que a afirmação não possa ser apagada por acidente.
- **Por que o módulo continua de posição única:** o limiar foi medido contra negativos obtidos
  por **busca na janela inteira** (0,4624 é o melhor casamento em qualquer posição de um frame
  sem painel). Ou seja, o limiar de 0,73 já é seguro para um consumidor que busca. Acrescentar a
  busca aqui seria escopo do 01-04 e contrariaria a lição medida do `identidade.py`.
- **Files:** `l2scanner/mercado_visao.py`, `l2scanner/calibracao.py`, `tests/test_mercado_ancora.py`
- **Committed in:** `50e68cd`

### 3. [Rule 2 - Missing Critical] O roteiro perguntava algo que já estava respondido

- **Found during:** Task 2, depois da descoberta 2
- **Issue:** O bloco "arraste o painel" do cenário `mercado-aberto` pedia ao usuário que
  descobrisse **se** o painel arrasta. Com isso medido, o pedido gastaria a atenção dele numa
  pergunta morta e deixaria de colher o que agora é a dúvida real: o **alcance** do movimento e
  se o painel reabre onde foi fechado — é isso que decide entre "procurar numa faixa" e
  "procurar na janela inteira" (~45 ms, caro demais para rodar a cada volta).
- **Fix:** o bloco virou três posições + fecha-reabre, com o número medido escrito. E o cenário
  `mercado-fechado` ganhou o pedido do banner de sistema, a classe de negativo mais difícil.
- **Files:** `ROTEIRO-SPIKE.md`
- **Committed in:** `fb3aad8`

### 4. [Rule 1 - Bug] `IMREAD_GRAYSCALE` e `BGR2GRAY` não dão o mesmo array

- **Found during:** Task 2, ao provar que o teste de fidelidade passaria contra `recordings/`
- **Issue:** O teste lia o frame de origem com `cv2.imread(p, IMREAD_GRAYSCALE)` e comparava com
  a fixture, que o resgate produziu por `cv2.cvtColor(cv2.imread(p), BGR2GRAY)`. Os dois caminhos
  de decodificação diferem em **até 1 por pixel** — invisível ao olho, suficiente para mover um
  casamento na terceira casa decimal e deixar vermelho um teste de valor medido.
- **Fix:** o teste passou a usar `BGR2GRAY`, o caminho **canônico** deste projeto porque é o que
  o consumidor real faz (a captura entrega BGR). A armadilha está escrita na docstring da classe,
  com o aviso de que re-resgatar pelo outro caminho move **todos** os valores medidos do arquivo.
- **Files:** `tests/test_mercado_ancora.py`
- **Committed in:** `50e68cd`

### 5. [Rule 3 - Blocking] `recordings/` não existe dentro do worktree

- **Found during:** Task 2, na avaliação da `<precondition>`
- **Issue:** A precondição pede `recordings/inv3/f000_JANELA.png`. O plano rodou num git worktree,
  e worktree **não materializa arquivo gitignored** — `recordings/`, `calibration.json` e `.venv`
  existem só no checkout principal. Avaliada ao pé da letra, a precondição estaria não-cumprida e
  a Task 2 pararia num portão que na máquina do usuário está satisfeito.
- **Fix:** o arquivo **existe no disco** (3,5 MB, em `Lineage2-warnings/recordings/inv3/`), que é
  o fato que a precondição afirma. O resgate leu os frames de lá em modo **somente leitura** e
  escreveu todos os artefatos dentro do worktree. Nenhum comando git, nenhuma escrita, nenhuma
  modificação fora do worktree.
- **Consequência permanente e desejada:** os dois testes que dependem de `recordings/` ficam em
  `pytest.skip` com a razão dita — o padrão literal de `TestOCasamentoNasFixturesVERSIONADAS`.
  Ambos foram exercidos manualmente contra o caminho real e **passam**; as fixtures resgatadas
  cobrem positivos, negativos e degenerados num clone limpo.

### 6. [Rule 3 - Blocking] `ruff` acusou 3 `E741` no script novo

- **Found during:** Task 1
- **Issue:** `l` como variável de comprehension, em três lugares do meu próprio código.
- **Fix:** renomeadas para `bruta` e `linha`. Nada mais no arquivo mudou.
- **Committed in:** `2fb8187`

---

**Total deviations:** 6 auto-corrigidas (2 bugs, 2 missing critical, 2 blocking)
**Impact:** Nenhum item do plano foi reduzido, adiado ou simplificado. As deviations 1 e 2 são o
retorno direto do de-risking: duas suposições da pesquisa foram desmentidas por medição **antes**
de o usuário gastar uma única sessão, e a segunda delas mudaria a arquitetura da detecção se
tivesse aparecido depois. Zero dependências novas; `requirements.txt` byte-idêntico.

## Issues Encountered

- **`calibration.json` da raiz tem `party_window_na_janela` com largura 174, mas os recortes
  gravados no `inv3` têm 172.** Diferença de 2 px, encontrada na conferência de geometria. **Não
  afeta este plano** — o retângulo da âncora foi medido direto sobre o frame de janela, nunca
  derivado da calibração. Afeta quem for derivar recortes de party dos frames `_JANELA` (o replay
  de regressão do 01-04): a calibração foi mexida depois daquela gravação. **Registrado aqui para
  o 01-04 conferir antes de confiar num recorte de party derivado.** A dimensão que este plano
  precisava — a da janela, 1720×1392 — bate em todos os 12 frames verificados.
- **Suíte no worktree tem baseline diferente da máquina do usuário** (1179/4 aqui contra 1181/2
  lá): o worktree não tem `.venv` nem as bindings de OCR, então 2 testes que lá passam aqui pulam.
  Não é regressão — medido rodando a suíte com e sem as duas suítes novas.

## Known Stubs

Nenhum. Nada nesta entrega devolve valor fixo, placeholder ou "coming soon". A única constante
numérica nova (`CASAMENTO_MINIMO_DA_ANCORA`) é medida e tem os três números da medição ao lado.

## Threat Flags

Nenhuma superfície nova além do `<threat_model>` do plano.

| Ameaça | Estado |
|---|---|
| T-02-01 Information Disclosure em `tests/fixtures/mercado/` | **MITIGADA** — 13 recortes 100×28 em cinza, sem nome de personagem e sem mensagem de jogador; o inventário exato está na tabela acima |
| T-02-02 Tampering em `Calibracao.carregar` | **MITIGADA** — trilho `.get` com versão congelada; `molde_de_hex` confere dimensões declaradas contra o tamanho real dos bytes antes do reshape, com teste dedicado |
| T-02-03 Elevation of Privilege (âncora → lógica de morte) | **MITIGADA** — `mercado_visao.py` é puro e não tem nenhum consumidor de decisão; `l2scanner/visao.py` e `l2scanner/rastreador.py` fora do diff, conferido |
| T-02-04 DoS de disco nas 8 sessões | **MITIGADA** — roteiro prescreve 30-60 s com o custo por minuto escrito; pré-voo obrigatório |
| T-02-SC Tampering na árvore de dependências | **VAZIA por construção** — zero instalações; `requirements.txt` byte-idêntico |

## Next Phase Readiness

**Pronto, e esperando só o usuário.**

- Tudo que podia ser construído antes das gravações está construído: gravador consertado (01-01),
  modo janela completa (01-01), roteiro, portão executável, técnica da âncora e limiar medidos.
- **O bloqueio é o declarado no ROADMAP**, e não mudou: só o usuário pode gravar o World Exchange.
- **Para o 01-03 (análise) e o 01-04 (calibração e detecção), já entra decidido:**
  - o painel **anda** — a superfície do 01-04 precisa **localizar** antes de comparar, e a
    cadência da busca é uma decisão sua, com o precedente dos 5 s do diálogo de desconexão;
  - o limiar 0,73 já sobrevive a negativos obtidos por busca na janela inteira;
  - o `calibration.json` já tem onde guardar âncora, molde, limiar e carimbo de geometria;
  - a divergência de 2 px na largura da party window precisa ser conferida antes de qualquer
    recorte de party derivado dos frames `_JANELA`.

---
*Phase: 01-funda-o-firewall-gravador-e-spike-de-campo (workstream mercado)*
*Halted at: Task 3 — portão externo (`gate="blocking-human"`)*
*Date: 2026-08-27*
