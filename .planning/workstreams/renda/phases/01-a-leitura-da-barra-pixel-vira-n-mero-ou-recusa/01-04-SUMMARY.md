---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 04
workstream: renda
subsystem: leitura-da-renda
status: complete
tags: [ocr, glifos, adena, nivel, recusa-nomeada, par, criterio-1]

requires:
  - phase: "01-01"
    provides: "renda_leitura (charter, RecusaDaRenda, _cruzar_as_escalas, exp_da_barra, recortar), renda_modo, as fixturas de campo e a de calibracao"
  - phase: "01-03"
    provides: "os retangulos e os TRES pisos por personagem no calibration.json"
  - phase: "01-05"
    provides: "renda_leitura._glifos_do_numero (a peneira de forma UNICA da fase) e os onze moldes 5x10 da fonte da barra"
provides:
  - "l2scanner.renda_leitura.adena_da_barra — a adena por GLIFO, sem OCR em caminho nenhum"
  - "l2scanner.renda_leitura.nivel_da_regiao — o nivel por OCR mascarado com cruzamento por abstencao"
  - "l2scanner.renda_leitura.inteiro_do_nivel — a gramatica de inteiro compartilhada pelo nivel e pela adena"
  - "l2scanner.renda_leitura.CamposDaRenda, LeituraDaRenda, ler_os_tres_campos, ler_a_renda"
  - "l2scanner.renda_leitura.o_exp_andou_para_tras, o_nivel_andou_para_tras, a_adena_saltou_ordem_de_grandeza, conferir_o_par"
  - "MOTIVO_DO_CONJUNTO_DE_MOLDES, MOTIVO_DA_PONTUACAO e os tres motivos de par"
  - "renda_modo imprimindo os TRES campos na grafia do jogo, com tres codigos de saida"
  - "tests/fixtures/renda/calibracao_de_fixture.json com renda_moldes_da_barra FUNDIDO (onze rotulos)"
  - "tests/fixtures/renda/montagem_completa.png — o criterio 1 verificavel SEM o jogo aberto"
affects:
  - "Fase 2 (REND-03): herda as tres regras de par como funcoes puras e o par de campo com o level up verdadeiro"
  - "tests/test_renda_tracer.py (o codigo de saida da montagem de nivel preto mudou para RECUSA)"
  - "tests/test_calibrar_renda_moldes.py (o estado 'sem moldes' passou a ser MONTADO e nao herdado)"

actuals:
  tokens: 31900
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "leitor de campo por GLIFO composto NOMEADAMENTE (mascara -> segmentacao no MESMO piso -> peneira -> ler_glifos -> gramatica), e nunca delegado a ler_celula"
    - "guarda de conjunto completo ANTES de qualquer pixel, com os rotulos faltantes por NOME e o conserto apontando para um COMANDO"
    - "estruturas de resultado DIFERENTES por campo (ValorDaRenda com `escalas`, ValorDaAdena com `glifos`): nunca afirmar guarda que o campo nao tem"
    - "regra de par como funcao PURA sobre um par por parametro, sem chamador de producao na fase sem memoria"
    - "portao de arvore de sintaxe por FUNCAO (o corpo de adena_da_barra nao chama o motor de texto), com controle positivo no leitor irmao"

key-files:
  created:
    - tests/test_renda_completa.py
    - tests/test_renda_par.py
    - tests/fixtures/renda/montagem_completa.png
  modified:
    - l2scanner/renda_leitura.py
    - l2scanner/renda_modo.py
    - tests/fixtures/renda/calibracao_de_fixture.json
    - tests/test_renda_tracer.py
    - tests/test_calibrar_renda_moldes.py
    - tools/resgatar_fixturas_da_renda.py

key-decisions:
  - "O merge dos moldes veio do `calibration.json` do usuario e nao de `tests/fixtures/renda/moldes_da_barra.json`, porque aquele arquivo nunca existiu: o `01-05` gravou direto na chave de topo do arquivo real. A fixtura versionada passou a ser a UNICA verdade versionada dos moldes"
  - "A recusa de personagem sem calibracao continua saindo com o codigo OPERACIONAL (1) e nao com o de recusa (3): a propria definicao do codigo 1 no plano — 'a ferramenta nao chegou a ler' — descreve exatamente esse caso, e o teste do `01-01` ja o afirmava"
  - "Um recorte de adena sem corrida nenhuma acima do piso vira CAMPO VAZIO no leitor, e nao a recusa de forma que a peneira devolve: a peneira so conhece corridas, e quem sabe o nome do campo e quem traduz"
  - "`_faltantes_do_conjunto` deriva os rotulos de `GLIFOS_DO_NUMERO` em vez de importar `calibrar_mercado.cobertura_dos_glifos`: o portao de fonte do `01-01` proibe o modulo puro de importar um calibrador, e a disciplina (faltante por NOME) e o que se copia"
  - "`inteiro_do_nivel` serve o nivel E a adena: a gramatica dos dois e a MESMA, e uma segunda funcao seria uma terceira gramatica de milhar nesta arvore"
  - "MEDIDO E ESCRITO: o caminho de glifo resolveu QUAL CAMPO e nao QUAL DIGITO — fora da banda ele substitui, e o teste que prova isso FALHA se a substituicao sumir"

patterns-established:
  - "Refutacao com a medicao ao lado no FONTE: as duas metades do LEIT-03 caem escritas, com o achado de cada uma"
  - "Teste que falha quando o mundo melhora: o controle da substituicao fora da banda exige que ela EXISTA, para que a prosa nao continue afirmando o que deixou de ser verdade"
  - "Portao com controle positivo compartilhando a MESMA funcao do portao (distincao de motivos, ausencia de memoria)"

requirements-completed: [LEIT-01, LEIT-03, LEIT-04, LEIT-07, LEIT-08, LEIT-09]

coverage:
  - id: D1
    description: "O comando de leitura unica imprime os TRES campos na grafia do jogo para um personagem nomeado, e o criterio 1 fecha num olhar"
    requirement: "LEIT-01"
    verification:
      - kind: e2e
        ref: "python -m l2scanner.renda_modo --imagem tests/fixtures/renda/montagem_completa.png --personagem Faerlina --calibracao tests/fixtures/renda/calibracao_de_fixture.json"
        status: pass
      - kind: unit
        ref: "tests/test_renda_completa.py::TestOComandoImprimeOsTresCampos"
        status: pass
    human_judgment: false
  - id: D2
    description: "A adena e lida por GLIFO e nunca por OCR, e os tres numeros que a medicao de campo capturou errados nao voltam em piso nenhum"
    requirement: "LEIT-09"
    verification:
      - kind: unit
        ref: "tests/test_renda_completa.py::TestOsControlesNegativosReais::test_A_GRADE_DE_PISOS_INTEIRA_NUNCA_DEVOLVE_UM_DOS_TRES"
        status: pass
      - kind: unit
        ref: "tests/test_renda_completa.py::TestQueAAdenaSaiuDoOCR::test_O_CORPO_DE_adena_da_barra_NAO_CHAMA_O_MOTOR_DE_TEXTO"
        status: pass
    human_judgment: false
  - id: D3
    description: "Conjunto de moldes ausente ou incompleto recusa nomeando os rotulos que faltam, e aponta o cortador como conserto"
    requirement: "LEIT-09"
    verification:
      - kind: unit
        ref: "tests/test_renda_completa.py::TestAGuardaDoConjuntoDeMoldes"
        status: pass
    human_judgment: false
  - id: D4
    description: "As tres recusas de par — EXP para tras, nivel para tras, adena saltando ordem de grandeza — com controle negativo REAL e portao de distincao"
    requirement: "LEIT-04"
    verification:
      - kind: unit
        ref: "tests/test_renda_par.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "A leitura e de UM personagem, com os retangulos e os tres pisos dele, e nunca cai no vizinho"
    requirement: "LEIT-07"
    verification:
      - kind: unit
        ref: "tests/test_renda_completa.py::TestALeituraEDeUmPersonagemNomeado"
        status: pass
    human_judgment: false
  - id: D6
    description: "Cada regiao usa o SEU piso, e o da adena e agora o do caminho de glifo (banda larga) e nao o do OCR"
    requirement: "LEIT-08"
    verification:
      - kind: unit
        ref: "tests/test_renda_completa.py::TestAAdenaContraPixelReal::test_A_BANDA_DE_GLIFO_E_LARGA_E_OS_DOIS_EXTREMOS_LEEM_IGUAL"
        status: pass
    human_judgment: false
  - id: D7
    description: "O criterio 1 conferido pelo OLHO, com o jogo aberto e a janela de status visivel, nas DUAS instancias"
    requirement: "LEIT-01"
    verification: []
    human_judgment: true
    rationale: "Nao ha CLI que olhe o monitor do usuario e diga que os tres numeros do terminal sao os tres numeros da tela de HOJE. Metade do criterio fechou offline contra o frame de campo com verdade escrita; o que o olho acrescenta e que a calibracao de hoje ainda bate com a tela de hoje, nas DUAS instancias (M-F)."

duration: ~1 sessao
completed: 2026-09-02
---

# Phase 01 Plan 04: Os tres campos no comando, e as recusas de par — Summary

**O criterio 1 esta FECHADO no desfecho (a): o comando imprime `nivel 67`, `EXP 8,0012%` e a
adena `13.160.684` como NUMERO, batendo com a verdade de campo, e sai em 0 — e a adena chega la
por GLIFO, com os tres numeros que o OCR errou presos por um controle negativo que varre a grade
de pisos inteira.**

## O desfecho, com numeros

O plano nomeou dois desfechos possiveis para a rodada final e disse que eles **nao valem a mesma
coisa**. O que saiu foi o **(a), "criterio 1 fechado"** — o unico que fecha a fase:

```
$ python -m l2scanner.renda_modo --imagem tests/fixtures/renda/montagem_completa.png \
      --personagem Faerlina --calibracao tests/fixtures/renda/calibracao_de_fixture.json
Faerlina  (montagem_completa.png)
  nivel  67 *
  EXP    8,0012%
  adena  13.160.684
 * sustentado por UMA escala de leitura so (a outra abstem): ali o cruzamento nao esta
   pegando substituicao de digito, e quem confere e o seu olho.
CODIGO=0
```

Os tres sao a verdade de campo de `01-MEDICOES-DE-CAMPO.md`. **O desfecho (b) — adena recusada por
conjunto incompleto — nao aconteceu**, e nao podia acontecer: a rodada de moldes do `01-05` fechou
os onze rotulos, e o merge da Tarefa 1 os poe na fixtura que este comando consome.

A adena lida pelo caminho de **producao** (`adena_da_barra`), contra as cinco fixturas versionadas,
no piso calibrado 185:

```
OK  aba_para_calibrar_f000       lido=2,207,577    esperado=2.207.577    glifos=9
OK  campo_faerlina_f000          lido=13,160,684   esperado=13.160.684   glifos=10
OK  campo_yazalaque_f001         lido=1,696,020    esperado=1.696.020    glifos=9
OK  segundo_cenario_faerlina     lido=15,134,779   esperado=15.134.779   glifos=10
OK  segundo_cenario_yazalaque    lido=4,497,890    esperado=4.497.890    glifos=9

5/5 corretos
```

E o desfecho de recusa, contra a montagem cuja regiao de nivel e preta de proposito:

```
Faerlina  (montagem_da_janela.png)
  nivel  RECUSADO (campo-vazio): as 2 escalas devolveram texto vazio: >>><<< >>><<<
  EXP    8,0012%
  adena  13.160.684
 -> o campo nao apareceu na mascara: confira o RETANGULO ou o PISO DE BRILHO desta regiao
    com `calibrar-renda.bat`
CODIGO=3
```

Um campo recusou, os outros dois continuaram saindo, o codigo distingue "recusou" de "leu" e de
"quebrou", e o rodape diz o conserto **daquele** motivo.

## Performance

- **Duracao:** ~1 sessao (a execucao foi cortada por limite de sessao entre a Tarefa 3 e o SUMMARY)
- **Tarefas:** 3 de 3
- **Commits:** 3 (um por tarefa, atomicos)
- **Arquivos tocados:** 9 (2 de producao, 4 de teste, 1 fixtura de dados, 1 fixtura de imagem, 1 ferramenta)
- **Testes novos:** 111 (75 em `test_renda_completa.py`, 36 em `test_renda_par.py`), **zero skips**

## Accomplishments

- **A adena saiu do OCR e virou glifo, com portao.** `adena_da_barra` compoe a cadeia
  nomeadamente — conjunto completo -> mascara -> segmentacao **no mesmo piso** -> a peneira do
  `01-05` -> `ler_glifos` -> `numero_valido` + `inteiro_de_quantidade` — e um portao de **arvore de
  sintaxe** afirma que o corpo dela nao chama o motor de texto, com **controle positivo** nos dois
  leitores irmaos (se o portao passasse num modulo sem OCR nenhum, ele nao provaria nada).
- **Os tres numeros que a medicao capturou errados estao presos.** Varrida a grade de pisos inteira
  (`0..255`, passo 5) sobre as **cinco** fixturas, `adena_da_barra` nunca devolve `106020`, nunca
  `91`, nunca `13091` e nunca `9790`. A mensagem de falha nomeia qual apareceu e cita o achado.
- **O nivel entrou por OCR mascarado com cruzamento por abstencao**, e o caso de campo do M-D esta
  afirmado: o nivel da Faerlina sai `67` com `escalas = 1`, porque a 2x abstem. Sob a regra antiga
  ele seria recusado **para sempre**.
- **As tres recusas de par nasceram puras**, com o **par de campo real** como controle negativo
  (Faerlina `66 / 68,5632% / 10.673.628` -> `67 / 8,0012% / 13.160.684`, um level up verdadeiro com
  as duas pontas gravadas), e os **tres** casos de numero valido-plausivel-errado com procedencia.
- **A guarda do conjunto incompleto e nao-cerimonial**, e o teste que prova isso passa um conjunto
  **sem o `5`** a um recorte cuja verdade contem um `5` (`15.134.779`) e afirma **recusa**.
- **O conserto que a recusa anuncia aponta para um COMANDO e nao para o tempo** — a correcao do M-L
  chegou na mensagem que o usuario le.

## Task Commits

1. **Tarefa 1: o nivel e a adena no modulo puro, e o merge dos moldes** — `7d17f0f` (feat)
2. **Tarefa 2: as tres recusas de par e o portao da distincao** — `96c3791` (feat)
3. **Tarefa 3: o comando imprime os tres campos** — `577070d` (feat)

## Files Created/Modified

- `l2scanner/renda_leitura.py` — `adena_da_barra` (glifo), `nivel_da_regiao` (OCR mascarado),
  `inteiro_do_nivel`, `_faltantes_do_conjunto`, `ValorDaAdena`, `CamposDaRenda`, `LeituraDaRenda`,
  `ler_os_tres_campos`, `ler_a_renda`, as tres regras de par e `conferir_o_par`, mais os cinco
  motivos novos. **`_ultimo_grupo_valido` nao nasceu**, e a refutacao dela esta escrita no lugar.
- `l2scanner/renda_modo.py` — as tres linhas na grafia do jogo, a marca de uma-escala-so com
  legenda, o conserto por motivo no rodape, o cabecalho com personagem e fonte de pixel.
- `tests/fixtures/renda/calibracao_de_fixture.json` — `renda_moldes_da_barra` **fundido**, com os
  onze rotulos, por load-mutate-save (10 chaves -> 11, nenhuma perdida, nenhuma alterada).
- `tests/fixtures/renda/montagem_completa.png` — a montagem do `01-01` com o recorte de campo do
  nivel colado na posicao de calibracao. A antiga fica: cada uma prova um desfecho.
- `tests/test_renda_completa.py` (novo, 75 testes) e `tests/test_renda_par.py` (novo, 36 testes).
- `tools/resgatar_fixturas_da_renda.py` — a segunda montagem, para que a proveniencia dela nao seja
  um script perdido.

## Medicoes que este plano produziu

### M-V — o caminho de glifo resolveu QUAL CAMPO, e nao QUAL DIGITO

Este e o achado da rodada, e ele **qualifica** a troca de leitor em vez de vende-la como fechada.

Varrendo a grade de pisos **passo 1** sobre as cinco fixturas, a leitura correta sai numa banda
larga, e **abaixo dela aparece substituicao**:

| fixtura | banda em que le CERTO | o que sai abaixo dela |
| --- | --- | --- |
| `campo_faerlina_f000` | 173–199 | (nada valido) |
| `campo_yazalaque_f001` | 174–200 | **`1.646.020`** nos pisos 170–173 — verdade `1.696.020` |
| `segundo_cenario_faerlina` | 177–200 | (nada valido) |
| `segundo_cenario_yazalaque` | 174–200 | (nada valido) |
| `aba_para_calibrar_f000` | 174–200 | **`2.247.577`** no piso 171 — verdade `2.207.577` |

`1.646.020` e um `9` casado como `4`, com a **gramatica de milhar inteira satisfeita e a forma do
recorte perfeita**. O piso calibrado e **185**, no meio da banda, e nenhuma substituicao aparece
dentro da banda medida (180–190).

**A consequencia esta escrita no fonte e no teste:** o caminho de glifo eliminou o sosia adjacente
— a L-Coin nunca mais sai —, e **nao** eliminou a substituicao de digito. Contra substituicao a
defesa continua sendo a **regra de par**, e e por isso que ela nao podia ser adiada para a Fase 2
mesmo que so a Fase 2 va chama-la.

O teste que prende isso (`test_O_CAMINHO_DE_GLIFO_NAO_E_IMUNE_A_SUBSTITUICAO_FORA_DA_BANDA`)
**falha se a substituicao sumir**, de proposito: a docstring afirma que ela existe, e uma afirmacao
que deixou de ser verdade tem de ser remedida em vez de continuar escrita.

### M-W — os numeros do M-G nao sao reproduziveis, porque o retangulo deles caiu

O M-G mediu o OCR da adena devolvendo `106.020` e `91` sobre `1500,1360 200x32`. **Aquele retangulo
foi refutado pelo M-O**, e o que vale hoje e `1540,1358 160x34`. Remedido nesta arvore sobre o
retangulo que vale:

```
campo_faerlina_f000    CRU: '' ''          <- M-E confirmado
   piso 185 (o calibrado):  '' ''          <- as duas escalas de OCR CEGAS
   piso 170:  '13,160.634' ''              <- comprimento certo, digito errado, PONTO no lugar da virgula
campo_yazalaque_f001   CRU: '' ''
   piso 185 (o calibrado):  '' ''
```

**No piso em que o caminho de glifo le os oito digitos certos, o OCR nao le nada nas duas escalas.**
O teste afirma esse par — cru vazio, mascarado invalido, glifo certo — em vez de citar um numero de
um recorte que nao existe mais. O veredicto do M-G (a adena sai do OCR) continua de pe, agora
sustentado por medicao reproduzivel a partir do clone.

## Decisions Made

Ver `key-decisions` no frontmatter. As duas que mais mudam o que existe:

- **A fixtura de calibracao virou a unica verdade versionada dos moldes.** `moldes_da_barra.json`
  nunca existiu; o `01-05` gravou direto no `calibration.json` do usuario, que e **gitignored**. Ter
  copiado os onze moldes para um segundo arquivo versionado criaria duas verdades sobre a mesma
  geometria — exatamente o que a docstring de `limite_de_glifo_unico` proibe.
- **A adena nao ganhou `escalas`, e por isso ela e uma CLASSE separada.** `ValorDaAdena` carrega
  `glifos` (quantos simbolos a peneira entregou), que descreve a guarda que aquele campo
  **realmente** tem. Um `escalas = 1` ali seria indistinguivel do `escalas = 1` do nivel, que
  significa outra coisa — la a segunda escala existe e abstem, aqui ela nunca existiu.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A fonte do merge dos moldes nao existia**
- **Found during:** Tarefa 1 (o primeiro passo, antes de qualquer codigo)
- **Issue:** O plano manda ler `tests/fixtures/renda/moldes_da_barra.json`. O arquivo **nao existe**:
  a rodada do `01-05` (`01-05-RODADA-DE-MOLDES.md`) gravou os onze moldes direto na chave de topo
  `renda_moldes_da_barra` do `calibration.json` da raiz, que e gitignored.
- **Fix:** o merge le a chave daquele arquivo e a escreve na fixtura por **load-mutate-save**
  (carregar o JSON inteiro, trocar so aquela chave, reemitir tudo). Nao foi criado um segundo
  arquivo versionado de moldes: isso criaria duas verdades sobre uma so geometria.
- **Verification:** `10 chaves -> 11, perdidas: nenhuma`; os dois personagens e os dois retangulos
  de nivel distintos afirmados por teste (`TestOMergeDosMoldesNaFixturaDeCalibracao`).
- **Committed in:** `7d17f0f`

**2. [Rule 3 - Blocking] O modulo puro nao pode importar `calibrar_mercado`**
- **Found during:** Tarefa 1
- **Issue:** o plano manda listar os rotulos faltantes com `calibrar_mercado.cobertura_dos_glifos`.
  O portao de fonte do `01-01` (`test_A_SETA_APONTA_FERRAMENTA_PARA_PURO_E_NUNCA_O_CONTRARIO`)
  proibe `from .calibrar*` em `renda_leitura.py` — e a proibicao esta certa: aquele modulo carrega
  `argparse` e consciencia de DPI no import.
- **Fix:** `_faltantes_do_conjunto` deriva os rotulos de `GLIFOS_DO_NUMERO`, que e **o mesmo
  conjunto** que `conjunto_descreve_numeros` compara — a mensagem nunca pode divergir do portao que
  a produziu. A disciplina (faltante por NOME, nunca por contagem) fica citada na docstring.
- **Committed in:** `7d17f0f`

**3. [Rule 2 - Correctness] Recorte de adena apagado dava recusa de FORMA e nao de campo vazio**
- **Found during:** Tarefa 1
- **Issue:** a clausula de comportamento pede que um recorte todo preto recuse por **campo vazio**.
  Sem corrida nenhuma acima do piso, `_glifos_do_numero` (do `01-05`) devolve `forma-do-recorte` —
  correto no vocabulario dela, que so conhece corridas, mas o usuario que le "forma" sobre uma tela
  preta vai procurar um numero que nao esta la, e o conserto e outro.
- **Fix:** `adena_da_barra` distingue os dois **antes** de chamar a peneira: sem runs, campo vazio
  nomeado, apontando para o retangulo ou o piso. **A peneira do `01-05` nao foi alterada** — a
  traducao mora do lado de quem sabe o nome do campo.
- **Verification:** `test_UM_RECORTE_TODO_PRETO_E_CAMPO_VAZIO` e
  `test_A_RECUSA_DE_CONJUNTO_E_DISTINTA_DAS_OUTRAS_TRES`.
- **Committed in:** `7d17f0f`

**4. [Rule 3 - Blocking] Tres testes de ondas anteriores dependiam da fixtura NAO ter moldes**
- **Found during:** Tarefa 1, ao rodar as suites anteriores depois do merge
- **Issue:** `test_renda_tracer.py::test_SEM_A_CHAVE_..._O_CAMPO_SAI_None`, `::test_AUSENTE_CARREGA`
  e `test_calibrar_renda_moldes.py::test_toda_outra_chave_de_topo_volta_IDENTICA` tomavam a ausencia
  da chave **emprestada** da fixtura. O merge — que e o produto desta tarefa — a derrubou.
- **Fix:** os tres passaram a **montar** o estado ausente com um `pop` explicito, com a razao e a
  data escritas na docstring. O que cada um prova continua identico; o que mudou e que a premissa
  virou construcao em vez de heranca silenciosa.
- **Committed in:** `7d17f0f`

**5. [Rule 3 - Blocking] O teste de ponta a ponta do `01-01` esperava codigo 0 na montagem de nivel preto**
- **Found during:** Tarefa 3
- **Issue:** `test_A_MONTAGEM_IMPRIME_O_EXP_COM_QUATRO_CASAS_E_SAI_EM_ZERO` afirmava saida 0. Com os
  tres campos na tela e a regiao do nivel preta, o desfecho certo passou a ser o codigo de **recusa**.
- **Fix:** o teste passou a esperar `SAIDA_RECUSA`, com a docstring dizendo que isso e o
  **cumprimento de uma promessa e nao uma regressao** — o proprio `01-01` registrou que aquela regiao
  preta viraria o caso de campo vazio do plano consumidor. O que ele continua provando (o EXP com
  quatro casas atravessando todas as camadas) esta intacto.
- **Committed in:** `577070d`

**6. [Rule 2 - Reproducibility] `tools/resgatar_fixturas_da_renda.py` estendido com a segunda montagem**
- **Found during:** Tarefa 1
- **Issue:** o arquivo nao esta em `files_modified`, mas ele e o **unico lugar** onde esta escrito
  como cada fixtura foi produzida. Gerar `montagem_completa.png` por um script solto deixaria a
  proveniencia dela fora do repositorio.
- **Fix:** a montagem virou a funcao `montar(destino, pecas)` e o modulo passou a produzir as
  **duas**, com o comentario dizendo que cada uma prova um desfecho do comando.
- **Committed in:** `7d17f0f`

### Decisao que contraria a letra do plano, e a razao

**7. [Rule 4 - Contradicao interna do plano] O personagem sem calibracao continua saindo com codigo 1**

O criterio da Tarefa 3 diz: *"Um personagem sem entrada na calibracao sai com o **codigo de
recusa**"*. Mas a **tabela de codigos do proprio plano** define o codigo 1 como *"a ferramenta nao
chegou a ler"*, e o charter do `renda_modo` que o `01-01` entregou lista *"personagem
desconhecido"* explicitamente no codigo 1 — com um teste que ja o afirmava
(`test_UM_PERSONAGEM_DESCONHECIDO_RECUSA_ANTES_DE_QUALQUER_OCR`).

O caso e literalmente "a ferramenta nao chegou a ler": a recusa sai **antes de qualquer OCR**, por
desenho. **Mantido o codigo 1.** O que o criterio realmente exige — *"e nao com codigo 0, nem com a
leitura do vizinho"* — esta satisfeito, e a recusa **nomeada** por personagem existe no modulo puro
(`MOTIVO_DO_PERSONAGEM` nos tres campos), com o conserto no rodape. Nao houve mudanca de
comportamento: o desacordo e entre duas frases do plano, e prevaleceu a que ja estava implementada
e testada.

---

**Total de desvios:** 6 auto-corrigidos (4x Rule 3, 2x Rule 2) + 1 decisao Rule 4 documentada.
**Impacto no plano:** nenhum criterio de aceitacao perdido. Um criterio (a fonte do merge) foi
satisfeito por outra fonte, e um (o codigo de saida do personagem) foi resolvido contra a letra e a
favor da tabela do proprio plano.

## Issues Encountered

- **A execucao foi cortada por limite de sessao** entre o commit da Tarefa 3 e a escrita deste
  arquivo. Nada ficou pela metade: os tres commits estavam feitos e a arvore limpa; o SUMMARY foi
  escrito na retomada, com todas as verificacoes **refeitas** em vez de citadas de memoria.
- **Os numeros do M-G nao eram reproduziveis** a partir do clone, porque o retangulo em que foram
  medidos ja tinha sido refutado pelo M-O. Resolvido remedindo sobre o retangulo que vale (ver M-W)
  em vez de escrever um teste que citasse um numero de um recorte inexistente.

## Verification

Refeito na retomada, com o `.venv` no `PYTHONPATH` (OCR disponivel):

- `python -m pytest tests/ -q --ignore=tests/test_agenda.py -p no:randomly` — **5227 passed,
  24 skipped**, contra a baseline de **5140 passed**.

  **A subtracao ingenua assusta e esta errada, entao ela vai desfeita aqui.** `5227 - 111 = 5116`
  parece 24 testes a menos que a baseline. Nao ha regressao: a coleta total e **5251**, e
  `5251 - 111 = 5140` — exatamente a baseline. O que mudou nao foi o resultado, foi o **ambiente**:
  a baseline foi medida no checkout principal e esta rodada num **worktree**, e os 24 skips sao
  todos de arquivo que o git ignora e que nao se materializa num worktree nem num clone limpo:

  | quantos | o que falta |
  | --- | --- |
  | 16 | `recordings/` (mercado replay, multiancora, ancora, 27x, inventario, sugestao de calibracao) |
  | 2 | o acervo real de imagens |
  | 1 | `calibration.json` |
  | 1 | `.env` |
  | 1 | `.venv/Lib/site-packages` dentro do worktree (`test_firewall_escopo`) |
  | 3 | os demais do mesmo grupo |

  Conferido um a um com `-rs`: **nenhum e de arquivo da renda**, e os dois arquivos novos deste
  plano pulam **zero**.
- `python -m pytest tests/test_renda_completa.py tests/test_renda_par.py -q -rs` — **111 passed,
  ZERO skips**. O caso do conjunto completo **nao pula**, e o caminho de glifo nao precisa de OCR:
  a adena, que e o campo mais perigoso da fase, e verificavel em qualquer clone.
- `python -m pytest tests/test_renda_tracer.py tests/test_calibracao_renda.py
  tests/test_calibrar_renda.py tests/test_calibrar_renda_nao_apaga_nada.py
  tests/test_renda_glifos.py tests/test_calibrar_renda_moldes.py
  tests/test_nenhum_numero_do_spike_no_fonte.py -q` — **0 failed**: as tres ondas anteriores seguem
  de pe, e nenhum limiar novo entrou como literal inteiro no fonte.
- `git diff --stat requirements.txt l2scanner/calibracao.py l2scanner/calibrar_renda.py
  l2scanner/calibrar_renda_moldes.py` — **vazio**. Nenhuma dependencia nova, e os arquivos dos
  outros planos nao foram tocados.
- O comando contra `montagem_completa.png` -> **codigo 0**, tres campos como numero.
  Contra `montagem_da_janela.png` -> **codigo 3**, nivel como campo vazio, EXP e adena como numero.
  Com `--personagem Yazalaque` sobre o frame da Faerlina -> o nivel **nao** e `67`.
  Com `--calibracao` inexistente -> **codigo 1**, sem traceback.

## Known Stubs

Nenhum. Nenhuma funcao deste plano devolve valor fixo, nenhum caminho de recusa e placeholder, e
nenhum teste foi marcado como `skip` ou `xfail`.

## O que fica ABERTO desta fase

**O `human-check` da Tarefa 3 nao foi executado.** Ele exige o jogo aberto, a janela de status
visivel e o olho do usuario comparando terminal e monitor **nas duas instancias** — e o agente nao
tem jogo aberto. Metade do criterio 1 esta fechada offline, contra o frame de campo cuja verdade
esta escrita (`67`, `8,0012%`, `13.160.684`); o que o olho acrescenta e que a calibracao de **hoje**
ainda bate com a tela de **hoje**.

Comando para a conferencia, uma vez por instancia:

```
vigiar-party.bat  (ou, direto)
python -m l2scanner.renda_modo --janela "<titulo da janela>"
```

**Conferir as DUAS**, e nao uma: o achado M-F diz que a calibracao de uma nao descreve a outra, e
conferir so uma deixaria passar exatamente o defeito que este plano existe para impedir.

## Divida nomeada, herdada e nao criada

O `01-05-RODADA-DE-MOLDES.md` registrou que `piso_de_leitura` (`0,4698`) e `margem_de_leitura`
(`0,0370`) foram **emprestados do par medido do mercado**, e que ninguem os mediu contra os glifos
desta barra — a matriz de confusao da barra tem pior par em `0,7171` e a ferramenta sugeria
`0,8586`. **Este plano consome os dois como estao** e nao os mexeu: com eles, as cinco fixturas leem
certo e os tres numeros errados nao voltam. A divida continua de pe e agora tem um numero ao lado:
o piso emprestado e folgado o bastante para deixar passar a substituicao do M-V **fora** da banda.
Medir o piso de leitura contra glifo desta barra e trabalho que ninguem fez ainda.

## Para a Fase 2

- As tres regras de par estao prontas como **funcoes puras** e **nenhum caminho de producao desta
  fase as chama** — um portao de arvore de sintaxe afirma isso, e outro afirma que o modulo nao
  ganhou memoria. Quem tem duas leituras e a Fase 2, e e la que `fator_de_salto` vem de cima.
- O **par de campo com o level up verdadeiro** vai junto, com as duas pontas e os horarios:
  Faerlina 2026-09-01 ~23h50 (`66 / 68,5632% / 10.673.628`) -> 2026-09-02 ~00h45
  (`67 / 8,0012% / 13.160.684`). A conta do REND-03 sobre ele — `(100 - 68,5632) + 8,0012 = 39,438`
  pontos percentuais em 55 minutos — **e da Fase 2**, e esta escrita aqui e no teste para que ela
  nao seja reinventada com numeros sinteticos la.
- `LeituraDaRenda` atravessa a fronteira com **tudo inteiro** e o carimbo por parametro: o modulo
  puro continua sem ler o relogio.

## Self-Check: PASSED

Os oito arquivos que este SUMMARY afirma existem em disco, e os tres commits existem em
`git log`. Conferido depois de escrever, e nao de memoria — a execucao foi cortada por limite de
sessao no meio, e citar de memoria e exatamente o que nao vale aqui.
