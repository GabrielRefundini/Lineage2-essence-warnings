---
phase: 01-reconhecimento-preciso-e-lista-de-bosses-no-config
workstream: tiat
plan: 04
subsystem: ferramentas-de-medicao
tags: [ocr, winrt, regex, difflib, recordings, medicao-de-campo]

requires:
  - phase: 01-01
    provides: "l2scanner/bosses.py — padrao_do_anuncio, padrao_do_nome; l2scanner/config.py — ler_bosses"
provides:
  - "tools/conferir_anuncio_de_boss.py — MotorDeOcr, Varredura, julgar, pista_do_boss, primeira_divergencia, imagens_de, regiao_da_calibracao"
  - "tests/test_conferir_anuncio_de_boss.py — 26 testes hermeticos, com o leitor de OCR injetado"
  - "README.md — a secao do aviso reescrita em termos da lista [[boss]] do config.toml"
  - "A EVIDENCIA DE CAMPO de R-01: a frase real, lida por OCR real, casando o padrao real"
affects: ["01-03 (a tabela de folga)", "Fase 2 (a ancora da janela de respawn)"]

actuals:
  tokens: 31500
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Ferramenta de medicao com o motor de OCR INJETADO, para a mecanica de veredito ser exercitada com o jogo fechado e sem as bindings WinRT"
    - "Pista de divergencia que pergunta a MECANICA DE PRODUCAO (padrao_do_nome por caractere) em vez de comparar por igualdade crua"
    - "Limiar de ferramenta medido contra DUAS populacoes nomeadas, com o corte no meio e os dois lados presos por teste"
    - "Varredura que PULA a imagem que nao cabe e so devolve erro quando NENHUMA coube — falha fechada sem jogar fora o corpus"

key-files:
  created:
    - tools/conferir_anuncio_de_boss.py
    - tests/test_conferir_anuncio_de_boss.py
  modified:
    - README.md

key-decisions:
  - "A ferramenta nao escreve regex propria: padrao_do_anuncio e padrao_do_nome sao importados (T-04-03), e o tripwire prova isso pela ARVORE e nao por substring"
  - "O texto cru sai em repr(), linha a linha, ANTES do veredito — o veredito sozinho nao distingue 'o OCR perdeu um caractere' de 'o padrao esta errado'"
  - "As duas escalas de OCR saem lado a lado porque a divergencia entre elas E o achado, e aponta para uma correcao diferente da de afrouxar o padrao"
  - "O piso da PISTA subiu de 0,6 para 0,65, MEDIDO: em 0,6 a varredura cuspiu 320 pistas com zero near-miss de verdade no meio"
  - "frame_*.png ganha de *.png em qualquer nivel: o recordings/ real tem 12 PNGs avulsos na raiz que sombreavam 2.110 frames nas subpastas"
  - "NENHUMA tolerancia foi aplicada em l2scanner/bosses.py — o arquivo e do 01-03, na mesma wave. A medicao virou item registrado."

patterns-established:
  - "Medir o sentido NEGATIVO contra texto de tela de jogadores reais, e nao contra strings inventadas por quem escreveu o padrao"
  - "Uma varredura de campo reporta os numeros MEDIDOS, inclusive quando eles contradizem a expectativa do plano (o plano esperava zero casamentos; foram 36 frames)"

requirements-completed: [RECO-01, RECO-04, VIGI-01, VIGI-02, VIGI-04, OPER-01]

coverage:
  - id: D1
    description: "Existe um comando que confronta a frase real contra o padrao, com o jogo fechado e sem rede, mostrando o texto cru das duas escalas ao lado do veredito por boss"
    requirement: RECO-01
    verification:
      - kind: unit
        ref: "tests/test_conferir_anuncio_de_boss.py::TestOVeredito"
        status: pass
      - kind: unit
        ref: "tests/test_conferir_anuncio_de_boss.py::TestOTextoCru"
        status: pass
      - kind: integration
        ref: "python -m tools.conferir_anuncio_de_boss recordings --regiao chat --recorte 20 880 600 470 (2.110 frames, codigo 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "O sentido NEGATIVO do padrao esta medido contra chat real de jogadores: 2.074 frames de chat movimentado, zero casamentos"
    requirement: RECO-01
    verification:
      - kind: integration
        ref: "varredura de 2.110 frames / 4.220 passadas de OCR — casamentos so nos 36 frames que contem o anuncio de verdade"
        status: pass
    human_judgment: false
  - id: D3
    description: "O sentido POSITIVO esta medido contra pixels reais: a frase do servidor, lida por OCR de verdade, dispara o alerta para o boss certo e nao para o outro"
    requirement: RECO-04
    verification:
      - kind: integration
        ref: "20260828-061409-mercado-alvo-sobreposto/frame_000011..046 — 36 frames, 72 passadas, 100% casaram para Tiat North e 0% para Tiat South"
        status: pass
    human_judgment: false
  - id: D4
    description: "O README descreve a vigilancia em termos da lista do config.toml, com os tres campos, a degradacao e a calibragem unica"
    requirement: OPER-01
    verification:
      - kind: automated_ui
        ref: "python -c \"...all(k in README for k in ('[[boss]]','respawn_horas_min','respawn_horas_max','has spawned','calibrar-tiat.bat'))\" -> 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Confirmacao humana de que o comportamento em campo bate com a medicao — o usuario ve o alerta chegar no WhatsApp no proximo spawn real"
    verification: []
    human_judgment: true
    rationale: "A varredura prova a cadeia pixels -> OCR -> padrao -> veredito. Ela NAO exercita o resto do caminho: extras do frame no laco de captura da janela, debounce ao vivo, e o POST no Chatwoot. Nenhuma gravacao do repositorio tem o scanner RODANDO durante um spawn."

duration: 96min
completed: 2026-08-30
status: complete
---

# Phase 1 Plan 04: A conferencia do anuncio de boss — Summary

**R-01 FECHOU COM EVIDENCIA DE CAMPO, e ela ja estava no repositorio: `recordings/20260828-061409-mercado-alvo-sobreposto` contem um nascimento REAL de `Tiat North`, e a ferramenta nova mostra o Windows OCR lendo `Tiat North [Lv. 60] has spawned!` daqueles pixels e o padrao do 01-01 casando em 36 frames seguidos, nas duas escalas, enquanto 2.074 frames de chat movimentado de jogadores nao casaram nenhuma vez.**

## Performance

- **Duration:** ~96 min (inclui os ~35 min da varredura de 4.220 passadas de OCR)
- **Tasks:** 3 de 3
- **Files modified:** 3 (2 criados, 1 modificado)
- **Suite:** 2197 passed / 14 skipped (baseline deste worktree, herdado do 01-01) -> **2223 passed / 14 skipped**. Zero testes existentes editados; zero enfraquecidos.

## 1. A VARREDURA — o que foi medido, e o numero que contradiz o plano

O plano previa **zero casamentos** e escreveu que zero seria o resultado desejado. **Foram 36 frames.** E nao e falso positivo: as gravacoes de `recordings/` ja continham um nascimento de verdade, gravado durante uma sessao real de farm em 2026-08-28, e ninguem tinha olhado.

### O comando, exatamente como rodou

```
.venv/Scripts/python.exe tools/conferir_anuncio_de_boss.py \
    C:/Users/refun/Desktop/Lineage2-warnings/recordings \
    --regiao chat --recorte 20 880 600 470
```

O `--recorte` explicito foi **obrigatorio**: os quatro `calibration*.json` do
checkout principal tem `tiat_chat: null` e `tiat_alvo: null` — a calibragem do
Tiat nunca foi feita nesta maquina. O retangulo `20 880 600 470` foi medido a
olho sobre `20260828-063240-mercado-farm-com-party/frame_000000.png` e cobre os
DOIS paineis de chat (o de sistema em cima, o geral embaixo). O `.venv` do
checkout principal foi usado porque e onde as bindings WinRT estao instaladas;
o Python do sistema nao as tem.

### Os numeros

| Medida | Valor |
|---|---|
| Frames varridos | **2.110** |
| Passadas de OCR (2 escalas por frame) | **4.220** |
| Gravacoes cobertas | **12** (as 12 pastas com `frame_*.png`) |
| Passadas sem texto nenhum | 6 (0,14%) |
| **Frames com casamento de ANUNCIO** | **36** |
| Passadas com casamento | 72 (36 frames x 2 escalas — **as duas concordaram em todos**) |
| Frames de chat real SEM casamento | **2.074** |
| Casamentos de `Tiat South` | **0** |
| Casos em que o anuncio APARECE no texto cru e o padrao NAO casou | **0** |

**Por gravacao:** os 72 casamentos estao todos em
`20260828-061409-mercado-alvo-sobreposto`, nos frames `000011` a `000046`,
**contiguos**. As outras 11 gravacoes — inclusive `20260827-225521-pre-voo`, com
**1.502 frames** de uma sessao de TvT/olimpiada com o chat geral fervendo —
produziram zero.

### O sentido NEGATIVO: 2.074 frames de chat de jogador, zero casamentos

E a primeira medicao de RECO-01 contra texto de tela escrito por gente de
verdade em vez de contra strings inventadas por quem escreveu o padrao. O
material e exatamente o que o `<specifics>` do CONTEXT descreve: varias
conversas simultaneas, recrutamento, anuncio de mercado, portugues e ingles
misturados. Amostra literal do que o OCR leu e o padrao recusou:

```
'SaBaoCruCru : VAGA DD AOE FILD PRA XP !!'
'Laurinhaa : alguma pt com vaga plains DD AEO'
'MST : LF DD AOE 55+ FIELDS MASSACRE'
'TwoB : as chances aqui nao sao justas, tem coisa de 80% falhando um bocado'
'That is an incorrect target. You feel the Fear Resistance Lv. 1 effect.'
```

### O sentido POSITIVO: a frase real, e como o OCR a entregou

As **74 ocorrencias** da frase no corpus (alguns frames a trazem duas vezes,
porque ela ecoa nos dois paineis de chat), agrupadas pela forma lida:

| n | casa? | forma lida pelo OCR |
|---:|---|---|
| 52 | SIM | `Tiat North [Lv. 60] has spawned!` |
| 8 | SIM | `Tiat North [Lv. 60] has spawned` (o `!` perdido) |
| 6 | SIM | `Tiat North [Lv. 60] has spawned!-` |
| 2 | SIM | `Tiat North [Lv. 60] has spawned!` (outro vizinho) |
| 2 | SIM | `Tiat North [Lv. 60] has spawned!` (outro vizinho) |
| 1 | SIM | `Tiat North [Lv. 60] has spawned!` (outro vizinho) |
| 1 | SIM | `Tiat North [Lv. 60] has spawned!` (outro vizinho) |
| **2** | **NAO** | **`Tiat North [Lv. 60] has spawn !`** |

**72 de 74 casaram sozinhas.** As 8 que perderam o `!` casaram porque o `!` ja e
opcional no padrao (D-09) — a decisao do CONTEXT esta **medida e confirmada**:
exigir a pontuacao teria produzido 8 falsos negativos.

**A redacao do print do usuario esta confirmada byte a byte**, inclusive o
`[Lv. 60]` que o ROADMAP supunha ser `[Lv. 80]`.

### A conferencia visual

O recorte de `frame_000011` foi inspecionado a olho. A linha do servidor esta
la, e o contexto ao redor dela e a melhor demonstracao de RECO-01 que este
projeto vai conseguir:

```
Kaus : Party inquiry
XRVinni : o pior que ele nasce no ultimo minuto      <- jogador FALANDO do spawn
XRVinni : e o das 9 vai nascer rapido                <- jogador FALANDO do spawn
Tiat North [Lv. 60] has spawned!                     <- o SERVIDOR
```

Dois jogadores conversando sobre o nascimento, na mesma tela, imediatamente
acima do anuncio de verdade — e **so o anuncio disparou**.

## 2. ACHADOS DE CAMPO — quatro coisas que a varredura mediu e que nao eram sabidas

Nenhuma delas foi aplicada. Todas sao itens para depois, com o numero medido ao
lado, porque os arquivos que as consertariam sao do `01-03` e do `ocr.py`.

### ACHADO A — a COR da linha do anuncio NAO e laranja. O CONTEXT esta errado.

O `<specifics>` do CONTEXT afirma: *"A linha aparece no chat com icone proprio e
em COR de sistema (laranja)"*. **Os pixels refutam.** Em
`frame_000011` a linha do anuncio e **CIANO, com icone de sino**, e o
**LARANJA e a cor do chat de COMERCIO dos jogadores** (`Ray : 2 slot aoe
massacre`, `kazekagee : RECRUTO WL PRA FARM EM FIELDS`).

**Por que isto importa e nao e trivia:** a alavanca deferida do CONTEXT
(*"Usar a COR da linha do chat como segunda confirmacao"*) teria sido
implementada **filtrando exatamente a cor errada** — ela teria descartado o
anuncio e admitido o chat de comercio, invertendo o recurso. Quem for pegar
aquela alavanca precisa comecar por remedir a cor. **Item para o CONTEXT da
Fase 2, nao para esta fase.**

### ACHADO B — `[Lv. NN]` NAO prova que a linha veio do servidor

O CONTEXT escreve que o nivel *"existe para provar que a linha e anuncio do
servidor e nao alguem digitando"*. **Medido: 323 das 4.220 leituras contem `Lv`
seguido de digito, e 251 delas nao tem nada parecido com um nome de boss.** As
formas mais comuns:

```
'... Fear Resistance Lv. 1 has worn off.'          (26+ ocorrencias)
'... Psycho has registered Pendant Nebula Lv. 2 on XM Market!'
```

Repare que `Lv. 1 has worn off` tem **`Lv`, um digito, e `has`** na mesma
sequencia. O que separa isso de um anuncio e o **nome do boss imediatamente
antes do `Lv`** e a palavra **`spawned`** — nao o nivel. A decisao D-11 continua
certa (o nivel entra no padrao e sai da decisao), mas a **justificativa escrita
no CONTEXT esta so meio certa**, e a Fase 2, que reavalia T-01-01 como `high`,
precisa saber que a margem e mais fina do que o texto sugere.

### ACHADO C — `splitlines()` e INERTE contra o OCR real

`VigiaDeBosses.avaliar` casa o anuncio **linha a linha** para impedir que o
`\s+` da parte fixa costure a linha de um jogador com a de outro (T-01-02), e o
`01-01` tem um teste que prova isso. **Medido: as 4.220 passadas devolveram
exatamente 1 linha. Nenhuma devolveu 2.** A causa esta em `l2scanner/ocr.py:280`
— `resultado.text` do WinRT junta as linhas com **espaco**, e nao com `\n`.
`splitlines()` sobre isso sempre devolve uma lista de um elemento.

O que sobra de protecao, e ele e real: o padrao nao tem `.*`, so `\s*`. Medido
nos quatro casos:

| caso | como chega | casa? |
|---|---|---|
| A) metades com texto de OUTRO jogador no meio, com `\n` | 2 linhas | NAO |
| B) o mesmo caso A, como o WinRT entrega | 1 linha | **NAO** |
| C) metades ADJACENTES, com `\n` | 2 linhas | NAO |
| D) **o mesmo caso C, como o WinRT entrega** | 1 linha | **SIM** |

Ou seja: o caso que o teste do `01-01` protege (A) continua protegido em
producao, mas **por outro motivo** — pela ausencia de `.*`, e nao pelo
`splitlines()`. O caso D fica **aberto**: uma linha de chat terminando
exatamente em `Tiat North` seguida da linha seguinte comecando exatamente em
`[Lv. 60] has spawned!` casaria. Isso e **T-01-01 (spoofing)**, hoje `accept`, e
que a Fase 2 ja tem obrigacao de reavaliar como `high`. **Item para o `01-03` ou
para a Fase 2; nao aplicado aqui.**

### ACHADO D — a tolerancia que a medicao indica, e por que ela NAO deve ser aplicada

**O caractere medido:** o `ed` final de `spawned`.
**A string exata:** `'Tiat North [Lv. 60] has spawn !'`
**Onde:** 2 das 74 ocorrencias (2,7%), nas duas escalas do mesmo frame.
**O teste que a acompanharia:** uma entrada na matriz de `TestOPadraoDoAnuncio`
com aquela string exata, no sentido positivo.

**E a recomendacao MEDIDA e NAO aplicar.** As razoes, em ordem de peso:

1. **Nao e um caso para `_FOLGA_DE_OCR`.** A tabela troca caractere por
   caractere; aqui o OCR **truncou** duas letras. Consertar exigiria tornar o
   `ed` de `spawned` opcional, e `has spawn` e muito mais perto de texto comum
   que `has spawned` — o afrouxamento comeria margem de RECO-01 no sentido
   errado.
2. **O defeito nao chega a produzir falso negativo.** Nos dois frames em que a
   forma truncada apareceu, o **mesmo blob** trazia uma segunda copia limpa (a
   frase ecoa nos dois paineis de chat), entao o veredito foi SIM. E o anuncio
   persiste **36 frames**; com o vigia lendo a cada 2 s, ele tem dezenas de
   oportunidades. **Zero frames do corpus perderam o anuncio.**
3. A varredura mediu **0** casos de "o anuncio aparece no texto cru e o padrao
   nao casou". O sentido positivo esta em 36/36.

Registrado para que ninguem afrouxe a parte fixa "de preventivo": a medicao
existe e ela diz para nao mexer.

## 3. O `<human-check>` da Task 3, VERBATIM

Reproduzido para o verificador da fase colher no `01-UAT.md`.

> 1. Salve o print do anuncio de nascimento (aquele com `Tiat North [Lv. 60] has spawned!`) num arquivo PNG, em qualquer pasta do projeto. Se voce tiver uma gravacao feita com `--record-janela` durante um spawn, ela serve melhor ainda.
> 2. Rode `python -m tools.conferir_anuncio_de_boss CAMINHO-DO-ARQUIVO --regiao chat`. Se o arquivo for um print da tela inteira e nao da janela calibrada, acrescente o recorte explicito em quatro inteiros que a ferramenta pede no `--help`.
> 3. Cole a saida inteira — o texto CRU lido nas duas escalas de OCR, e o veredito por boss.
> 4. O que cada resultado significa:
>    - **CASOU para `Tiat North` e nao para `Tiat South`:** e o desfecho esperado. R-01 fecha, e o texto cru vira a primeira evidencia de campo que este projeto tem da frase do anuncio.
>    - **NAO CASOU, com o texto cru mostrando a frase quase certa:** este e o resultado UTIL, nao um fracasso. O texto cru diz exatamente qual caractere o OCR perdeu. A correcao e UMA entrada a mais na tabela de folga de OCR, nomeando o caractere medido, mais um teste na matriz com a string exata — **registrada no SUMMARY como item para depois, e NAO aplicada aqui**: aquele arquivo e do `01-03`, que roda nesta mesma wave. Nao afrouxe a parte fixa inteira para resolver de uma vez.
>    - **NAO CASOU e o texto cru esta irreconhecivel:** o problema nao e o padrao, e a escala de leitura. A saida mostra as duas escalas lado a lado; se a de conferencia le e a de deteccao nao, a correcao e o scanner ler o recorte do chat na escala maior — e isso e um item novo para o roadmap, nao um remendo no padrao.
>    - **Voce nao tem o print nem uma gravacao com o anuncio:** responda isso. E um desfecho aceitavel e ele fica EXPLICITO: R-01 permanece ABERTO no `STATE.md`, a fase fecha com a tolerancia baseada na redacao medida do print e nao nos pixels, e a Fase 2 nao pode ancorar nada antes de a primeira deteccao real ser conferida com esta ferramenta.
> 5. Mesmo que tudo de NAO, colar a saida e sempre a acao certa: a ferramenta imprime o texto cru antes de qualquer veredito, entao a saida e informacao em todos os casos.

**NOTA PARA O VERIFICADOR, e ela muda o que pedir.** O ramo 1 deste bloco **ja
aconteceu, sem o usuario**: a varredura sobre `recordings/` achou o anuncio real
e ele casou em 36 frames, nas duas escalas, sem casar `Tiat South`. Pedir o
print de novo nao acrescenta evidencia. **O que ficou por confirmar e outra
coisa** — ver D5 na tabela de coverage: a varredura prova a cadeia
`pixels -> OCR -> padrao -> veredito`, e nao prova o resto do caminho (os
`extras` do frame no laco de captura da janela, o debounce ao vivo, e o POST no
Chatwoot). Nenhuma gravacao do repositorio tem o **scanner rodando** durante um
spawn. A pergunta certa para o usuario passou a ser *"no proximo nascimento, o
alerta chegou no WhatsApp?"*.

## 4. O estado de R-01

**FECHADO, com evidencia de campo, e sem depender do usuario.**

| O que R-01 duvidava | Como ficou |
|---|---|
| A redacao da frase e asserção do usuario | **Confirmada** em pixels: `Tiat North [Lv. 60] has spawned!`, inclusive o `[Lv. 60]` que o ROADMAP supunha ser 80 |
| Nunca atravessou o pipeline de OCR deste projeto | **Atravessou**: 74 leituras, 72 delas limpas, nas duas escalas |
| A folga de OCR e palpite e nao medicao | **Medida**: o `!` opcional (D-09) salvou 8 de 74 leituras; nenhuma outra tolerancia foi necessaria |
| O padrao pode nao casar a frase real | **Casou** em 36 de 36 frames, 72 de 72 passadas |
| O padrao pode casar chat de jogador | **Nao casou** em 2.074 frames de chat movimentado |

**O que continua aberto** e menor e esta nomeado em D5: a cadeia depois do
veredito (extras do frame no replay, debounce ao vivo, POST no Chatwoot) nao foi
exercitada contra um spawn, porque nenhuma gravacao tem o scanner rodando
durante um. A Fase 2 pode ancorar no reconhecimento; o caminho de entrega e que
ainda pede a confirmacao de campo.

## 5. Task Commits

| # | Tarefa | Commit | Tipo |
|---|--------|--------|------|
| 1 | RED — a regua da conferencia | `c392f22` | test |
| 1 | GREEN — a ferramenta | `35b9ff7` | feat |
| 2 | O README em termos da lista de bosses | `bd299a5` | docs |
| 3 | Os dois defeitos que a varredura do `recordings/` real revelou | `f6f4f01` | fix |
| 3 | O piso da PISTA, de 0,6 para 0,65, medido em campo | `79f2d30` | fix |

## Files Created/Modified

- `tools/conferir_anuncio_de_boss.py` — **criado.** Recebe um PNG, uma pasta de gravacao ou a pasta DE gravacoes; recorta pela calibracao ou por `--recorte`; le nas duas escalas; imprime o texto cru em `repr()` linha a linha e o veredito por `[[boss]]`; devolve 0 quando mediu e 1 quando nao conseguiu medir.
- `tests/test_conferir_anuncio_de_boss.py` — **criado.** 26 testes hermeticos, com o `MotorDeOcr` injetado. Rodam com o jogo fechado, sem rede e sem as bindings WinRT.
- `README.md` — **um unico hunk**, so a secao do aviso.

## Decisions Made

1. **O motor de OCR e um parametro, e nao um import direto.** Sem isso a mecanica de veredito — o unico pedaco que decide alguma coisa — so seria exercitada nas maquinas que ja tem o motor, que sao justamente as unicas onde ela nao precisa ser provada.
2. **O tripwire de T-04-03 prova pela ARVORE.** Um `assert "re.compile" not in fonte` acusava a propria docstring que EXPLICA a mitigacao, e o conserto teria sido apagar a explicacao. Pelo `ast`, `import re` e impossivel sob qualquer apelido, inclusive `import re as _r`, que um scan de substring deixaria passar.
3. **A pista pergunta a mecanica de producao, caractere a caractere.** `padrao_do_nome(caractere).fullmatch(lido)` responde se o par ja e tolerado. Por igualdade crua, a pista acusaria o `0` lido no lugar do `o` — uma troca que a folga JA aceita — e mandaria alguem afrouxar o que nao esta apertado. E o comeco do caminho que devolve o padrao ao curinga (T-04-01).
4. **A pista SUGERE e nunca decide.** Ela nao altera veredito nenhum; o limiar dela so escolhe quando gastar uma linha de saida.

## Deviations from Plan

### 1. [Rule 1 - Bug] Os PNGs avulsos da raiz sombreavam 2.110 frames

- **Encontrado durante:** Task 3, na primeira tentativa de varrer `recordings/`.
- **Problema:** a ordem de busca era `frame_*.png`, `*.png`, `*/frame_*.png`. O `recordings/` real tem **12 PNGs soltos na raiz** (`agora_janela.png`, `base_party.png`, recortes de party de outro recurso) e 2.110 frames nas subpastas. `*.png` casava os 12 e a busca parava — uma varredura que parece completa e cobre **0,5%** do material.
- **Solucao:** `frame_*.png` passa a ganhar de `*.png` em qualquer nivel. Preso por `test_os_frames_das_subpastas_ganham_dos_PNGs_avulsos_da_raiz`.
- **Commit:** `f6f4f01`

### 2. [Rule 1 - Bug] Uma imagem que nao cabia derrubava a varredura inteira

- **Encontrado durante:** Task 3, na mesma tentativa. `agora_party.png` e 172x522 (recorte de party window de outro recurso) e o recorte de chat nao cabe nele.
- **Problema:** a ferramenta abortava com codigo 1 no primeiro recorte que nao coubesse. Num `recordings/` que mistura frame de janela inteira com recorte de party, isso joga fora dois mil frames bons por causa de um arquivo que nem era chat.
- **Solucao:** a imagem e **PULADA com o motivo nomeado** e a varredura segue; codigo 1 so quando **NENHUMA** imagem coube. O que continua fechado e o que importa: nenhum recorte truncado, e zero leituras nunca vira zero casamentos (T-04-02).
- **Commit:** `f6f4f01`

### 3. [Rule 1 - Bug] O piso da PISTA em 0,6 produzia 320 linhas de ruido

- **Encontrado durante:** Task 3, na varredura completa.
- **Problema:** 0,6 (o corte que `difflib.get_close_matches` usa por padrao) produziu **320 linhas PISTA com zero near-miss de verdade no meio**. `'tion for T'` sozinho disparou 112 vezes; `'target. Th'` 68. Uma pista que dispara 320 vezes enterra a unica que importa no dia em que o usuario colar o print do spawn — que e exatamente o defeito que a ferramenta existe para evitar.
- **Solucao:** as duas populacoes foram medidas e **nao se sobrepoem** (pior near-miss `0,700` em `'T1at N0rlh'`; pior ruido `0,600`). Corte no meio, em **0,65**, com os dois lados presos por teste parametrizado.
- **Commit:** `79f2d30`

### 4. [Contrato da Task 3] O commit da Task 3 tocou `tests/`, e nao so `tools/`

- **O criterio literal:** *"`git diff --name-only` sobre a tarefa mostra apenas `tools/`"*.
- **O que aconteceu:** os tres consertos acima sao mudancas de comportamento da ferramenta, e este projeto nao aceita mudanca de comportamento sem teste. Os commits `f6f4f01` e `79f2d30` incluem `tests/test_conferir_anuncio_de_boss.py`.
- **Por que isto respeita o criterio onde ele importa:** o proposito escrito do `<nao_edita>` e proteger `l2scanner/bosses.py` do `01-03`, que roda na mesma wave. **`git diff --name-only 5e83a17..HEAD` devolve exatamente `README.md`, `tests/test_conferir_anuncio_de_boss.py`, `tools/conferir_anuncio_de_boss.py`.** Zero arquivos de `l2scanner/`, zero `config.toml`, zero `calibrar-tiat.bat`, zero `.planning/` fora deste SUMMARY. Conferido e colado na secao Verification.
- **A alternativa foi considerada e recusada:** commitar `tools/` sozinho deixaria um commit intermediario com a suite vermelha, o que viola uma garantia mais forte.

### 5. [Precisao de teste] Duas asseracoes do RED foram apertadas no GREEN

- `test_o_texto_cru_sai_ANTES_do_veredito` comparava posicoes a partir do topo da saida, e o cabecalho ja nomeia os bosses lidos do config — media o cabecalho. Passou a comparar dentro do bloco da leitura, e ganhou uma asseracao a mais (`veredito:`).
- `test_a_ferramenta_nao_escreve_expressao_regular_propria` passou de scan de substring para inspecao de `ast` (decisao 2 acima).
- **As duas ficaram mais fortes, nunca mais fracas.**

---

**Total de desvios:** 5 (3 Rule 1, todos achados pela varredura de campo; 1 de contrato, com o proposito preservado e conferido; 1 de precisao de teste). **Nenhum enfraquece asseracao, nenhum expande escopo, nenhum toca `l2scanner/`.**

## Issues Encountered

**Um teste alheio falhou uma vez, por carga de CPU.** `tests/test_janela_de_selecao.py::TestODrenoDaFilaDeTeclas::test_dreno_por_tempo_e_nao_por_numero_de_sondagens` falhou numa rodada executada **enquanto a varredura de 4.220 passadas de OCR ocupava a maquina**. Ele passa isolado e passa na suite inteira com a maquina livre (2223 passed). E um teste sensivel a relogio de parede; nao foi tocado e nao tem relacao com este plano. Registrado porque quem rodar a suite durante uma varredura pesada vai tropecar nele.

**A calibragem do Tiat nao existe nesta maquina.** Os quatro `calibration*.json` do checkout principal tem `tiat_chat: null` e `tiat_alvo: null`. Por isso a varredura usou `--recorte` explicito, e por isso o caminho `regiao_da_calibracao` — que traz o retangulo de coordenadas de DESKTOP para dentro da JANELA usando `party_window - party_window_na_janela` — **nao foi exercitado contra dado real**. Ele tem teste unitario do ramo de recusa, mas a aritmetica da origem so sera confirmada quando alguem rodar `calibrar-tiat.bat`.

## Known Stubs

Nenhum. Nao ha valor codificado que chegue a saida, nem caminho sem fonte de dados, nem `TODO`/`FIXME` introduzido por este plano.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. As tres mitigacoes `mitigate` estao implementadas e afirmadas:

| Ameaca | Mitigacao implementada | Teste |
|---|---|---|
| T-04-01 (afrouxar o padrao a partir de uma medicao) | A pista SUGERE e nunca decide; ela pergunta a folga se o par ja e tolerado antes de acusar; e o ACHADO D registra a unica tolerancia indicada **com a recomendacao medida de nao aplica-la** | `test_a_pista_nao_acusa_troca_que_a_folga_JA_aceita` |
| T-04-02 (OCR indisponivel confundido com "nenhum casamento") | Codigo 1 com o motivo impresso e sem varredura; e codigo 1 tambem quando nenhuma imagem coube no recorte | `test_ocr_indisponivel_devolve_1_e_imprime_o_motivo`, `test_recorte_que_nao_cabe_em_imagem_NENHUMA_devolve_1` |
| T-04-03 (`nome` do `[[boss]]` com metacaractere) | Zero regex propria; `padrao_do_anuncio`/`padrao_do_nome` importados | `test_a_ferramenta_nao_escreve_expressao_regular_propria` (por `ast`) |

T-04-04 (`accept`) foi respeitada: a ferramenta imprime no console local e **nao grava nem envia nada**. A saida da varredura ficou em diretorio temporario, fora do repositorio, e nenhum trecho de chat de jogador identificavel foi versionado — as amostras coladas neste SUMMARY sao linhas de recrutamento e mercado, sem conteudo privado.

## Verification

| Comando | Resultado |
|---|---|
| `python -m pytest tests/test_conferir_anuncio_de_boss.py -q` | **26 passed** |
| `python -m pytest tests/ -q` | **2223 passed, 14 skipped** (baseline 2197 / 14) |
| `python -m tools.conferir_anuncio_de_boss --help` | apresenta os cinco argumentos |
| varredura sobre `recordings/` (2.110 frames) | **codigo 0**, 36 frames com casamento, 2.074 sem |
| `python -c "...README tem [[boss]], respawn_horas_min, respawn_horas_max, has spawned, calibrar-tiat.bat..."` | rc=0 |
| `git diff README.md \| grep -c "^@@"` | **1** — um unico hunk |
| `git diff --name-only 5e83a17..HEAD` | `README.md`, `tests/test_conferir_anuncio_de_boss.py`, `tools/conferir_anuncio_de_boss.py` |
| `git diff --stat 5e83a17..HEAD -- l2scanner/ config.toml calibrar-tiat.bat requirements.txt .planning/` | **vazio** — nada protegido tocado, nenhuma dependencia nova |

## Self-Check

Executado antes de escrever esta secao.

**Arquivos afirmados como criados:**
- `tools/conferir_anuncio_de_boss.py` — FOUND
- `tests/test_conferir_anuncio_de_boss.py` — FOUND

**Arquivos afirmados como modificados:**
- `README.md` — FOUND, um hunk

**Commits afirmados:** `c392f22`, `35b9ff7`, `bd299a5`, `f6f4f01`, `79f2d30` — todos FOUND em `git log`.

**Evidencia de campo afirmada:** `recordings/20260828-061409-mercado-alvo-sobreposto/frame_000011.png` a `frame_000046.png` — FOUND no checkout principal, 47 frames na pasta, 36 com casamento.

## Self-Check: PASSED
