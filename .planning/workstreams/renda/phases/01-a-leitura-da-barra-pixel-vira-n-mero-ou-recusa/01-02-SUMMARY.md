---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 02
workstream: renda
subsystem: bancada-de-medicao-da-renda
status: complete
tags: [bancada, medicao, ocr, censo, banda-de-brilho, refutacao]
requires:
  - "01-01: renda_leitura._cruzar_as_escalas, decimos_de_milesimo, recortar, MOTIVO_*"
  - "01-01: Calibracao.renda_do_personagem, REGIOES_DA_RENDA"
  - "01-01: tests/fixtures/renda/calibracao_de_fixture.json"
provides:
  - tools/medir_a_renda.py (RELATORIO 1 varredura de piso; RELATORIO 2 censo dos quatro desfechos)
  - "01-MEDICOES.md: a taxa de discordancia com denominador, e 12 refutacoes citadas e respondidas"
  - "o numero que sustenta a recusa por discordancia no 01-04: 2/124 no nivel"
  - "o numero que sustenta o LEIT-09 com denominador: 5/10 aceitas erradas na adena"
affects: []
tech-stack:
  added: []
  patterns:
    - "a bancada LE a decisao de producao (`_cruzar_as_escalas`) em vez de escrever uma segunda particao"
    - "banda ACEITA e banda CERTA impressas lado a lado: a diferenca entre elas e onde mora o perigo"
    - "convencao de largura DECLARADA no topo do arquivo, porque um pixel ja custou uma refutacao (M-P)"
    - "uma reproducao que so pode concordar nao prova nada: DISCORDA e resultado valido e sai escrito"
key-files:
  created:
    - tools/medir_a_renda.py
    - tests/test_medir_a_renda.py
    - .planning/workstreams/renda/phases/01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa/01-MEDICOES.md
  modified: []
decisions:
  - "A taxa de discordancia entre leituras VALIDAS nao veio zero: 2/124 no nivel (1,6%). A recusa por discordancia FICA, e agora por medicao e nao por anedota"
  - "Concordancia entre 2x e 3x NAO e evidencia de acerto em campo nenhum: 3 das 4 leituras de nivel aceitas-e-erradas sao ACEITA-2-ESCALAS, e ali nao ha sosia gramatical"
  - "A tabela de bandas do M-E nao sobreviveu a reproducao por codigo: 11 das 12 comparacoes DISCORDAM"
  - "A largura de banda desta bancada conta PISOS DA GRADE, inclusiva -- e nao e a convencao de larguras_de_molde (M-P)"
  - "A gramatica do nivel e da adena vem de mercado_leitura porque renda_leitura ainda nao tem uma, e isso vai dito em voz alta em vez de inventado"
metrics:
  duration: ~1 sessao
  completed: 2026-09-02
actuals:
  tokens: 46000
  tasks: 2
  commits: 2
---

# Phase 01 Plan 02: A bancada de medição da renda — Summary

A varredura de piso que foi feita à mão numa madrugada agora roda por comando, por região e por
personagem — e ela **derruba** a tabela manual em 11 das 12 comparações; e a taxa de discordância
entre leituras válidas, que nunca tinha sido medida, é **2 em 124 no nível**, com os dois casos
sendo exatamente o valor errado que a concordância entre as duas escalas aceitou noutro frame.

## O que foi construído

### `tools/medir_a_renda.py` — a bancada, com dois relatórios sobre a MESMA passada de OCR

**RELATÓRIO 1 — a varredura de piso por região e por personagem.** Grade de 100 a 250 **de 5 em 5**
(31 pisos), as duas escalas sempre, e por piso: os dois textos crus entre `>>><<<`, os dois
inteiros, o desfecho do cruzamento, o valor e o veredicto contra a verdade de campo. Ao fim de cada
região: a **BANDA ACEITA** e a **BANDA CERTA** lado a lado, cada uma com a largura e os dois
extremos nomeados, a marca de **FRÁGIL** para largura 1 ou 2 com a razão impressa, a banda que o
M-E registrou, e o veredicto `BATE` / `DISCORDA` / `SEM-TABELA`.

**RELATÓRIO 2 — o censo dos quatro desfechos com denominador.** Unidade:
`(gravação, frame, personagem, região, piso)` — 4 frames × 31 pisos = **124 por campo**. Mais: quem
sustentou cada `ACEITA-1-ESCALA`, quantas leituras foram recusadas por **ambiguidade** de gramática
(o confundidor, exposto de propósito), e a **quinta contagem** — de todas as leituras ACEITAS com
verdade de campo escrita, quantas estavam ERRADAS.

Decisões que valem repetir:

- **O censo importa `renda_leitura._cruzar_as_escalas`.** `desfecho_do_cruzamento` apenas **lê** o
  que aquela função devolveu (o tipo, o `motivo`, o `escalas`). Uma segunda partição mediria a
  ferramenta e não o produto.
- **`conferir_o_passo` RECUSA passo maior que 5**, com o `155`, o `106.020` e o `1.696.020` na
  mensagem — porque quem for encurtar o tempo da varredura vai olhar o passo primeiro, e vai
  encontrar a recusa antes de encontrar a conclusão errada do M-E.
- **A convenção de largura vai declarada no topo**: contagem de **pisos da grade, inclusiva**
  (`180..190` com passo 5 vale 3), com o vão em níveis de V (`fim - inicio`, exclusivo) impresso ao
  lado. E dito em voz alta que ela **não** é a de `larguras_de_molde` — não são a mesma grandeza,
  mas foi um número sem convenção (o `17` do M-I) que já custou uma refutação a esta fase (M-P).
- **A peneira barata vem primeiro**: o dono do frame se decide pelo **nome do arquivo**, antes de
  abrir o PNG. O lote inteiro de `recordings/` tem 2379 frames sem personagem no nome, e lê-los
  todos custaria minutos por nada.
- **A ferramenta lê as gravações; nenhum teste lê.** E o nome da pasta não aparece nem por escrito
  em `tests/test_medir_a_renda.py`, pela mesma disciplina que `renda_leitura.py` aplica às chamadas
  de janela do OpenCV: um critério que aceitasse menção em comentário deixaria de pegar a abertura
  de verdade no dia em que ela entrasse comentada.

### `tests/test_medir_a_renda.py` — 55 testes, sem disco, sem OCR

O passo da grade (com o controle negativo: uma grade de 10 em 10 **pula** o 155), a peneira de dono
do frame, a peneira de forma, a gramática de inteiro, a leitura dos quatro desfechos contra
`_cruzar_as_escalas` de verdade, o resumo da banda com a largura, a marca de frágil, a contagem do
censo com denominador e a comparação contra a tabela de campo.

### `01-MEDICOES.md` — os veredictos

Dez seções de topo. Cinco perguntas respondidas **por citação** (M-A a M-F, M10, pesquisa c3), sem
remedição e sem que nenhuma suma. A sexta medida com denominador. A varredura reproduzida numa
seção própria. E **12 refutações** citadas e respondidas — as 5 do corpo do documento de campo, as
3 do Adendo, e 4 novas desta rodada.

## Os números desta rodada (2026-09-02, uma rodada)

### A pergunta que este plano existia para responder

| campo | n | 2 escalas | 1 escala | ilegível | **discordância** |
|---|---|---|---|---|---|
| EXP | 124 | 21 (16,9%) | 11 (8,9%) | 92 (74,2%) | **0 (0,0%)** |
| ADENA *(caminho abandonado, LEIT-09)* | 124 | 1 (0,8%) | 10 (8,1%) | 113 (91,1%) | **0 (0,0%)** |
| NÍVEL | 124 | 23 (18,5%) | 17 (13,7%) | 82 (66,1%) | **2 (1,6%)** |

**A guarda não dorme, e a razão é melhor que a taxa.** Os dois casos de discordância leem `65`
contra `69` (`20260902-093000-renda-segundo-cenario/frame_yazalaque.png`, pisos 175 e 190). E `65`
é *exatamente* o valor que a regra do cruzamento **aceitou com as duas escalas concordando** na
gravação de 00h45, nos pisos 175 e 180 da mesma personagem. A recusa por discordância pegou, nesta
árvore, o erro que a concordância deixou passar.

### A quinta contagem — aceitas e erradas

| campo | aceitas com gabarito | erradas | taxa |
|---|---|---|---|
| EXP | 27 | 3 | 11,1% |
| **ADENA** | **10** | **5** | **50,0%** |
| NÍVEL | 18 | 4 | 22,2% |

A linha da adena é o **M-G com denominador**, e ela **confirma** o LEIT-09. Somada à banda certa de
largura **zero** na Faerlina de 09h30 (nenhum dos 31 pisos lê a adena correta), o veredicto de tirar
aquele campo do OCR não precisa de mais argumento.

### A varredura contra a tabela de campo — 11 DISCORDA, 1 BATE

| personagem | região | BANDA CERTA (ou ACEITA quando não há gabarito) | M-E | veredicto |
|---|---|---|---|---|
| Faerlina 00h45 | EXP | 140..170 (7) | 150..170 | DISCORDA |
| Faerlina 00h45 | ADENA | 150..160 (3) | 150 | DISCORDA |
| Faerlina 00h45 | NÍVEL | 190..215 (6) | 190..220 | DISCORDA |
| Yazalaque 00h45 | EXP | 125..170 (10) | 130..170 | DISCORDA |
| Yazalaque 00h45 | ADENA | 145 (1, FRÁGIL) | 110 e 150 | DISCORDA |
| Yazalaque 00h45 | NÍVEL | 185..215 (7) | 170..210 | DISCORDA |
| Faerlina 09h30 | EXP | *aceita* 160..180 (5) | 150..170 | DISCORDA |
| Faerlina 09h30 | ADENA | **0 pisos** | 150 | DISCORDA |
| Faerlina 09h30 | NÍVEL | *aceita* 165..220 (12) | 190..220 | DISCORDA |
| Yazalaque 09h30 | EXP | 135..165 (7) | 130..170 | DISCORDA |
| Yazalaque 09h30 | ADENA | *aceita* 110 (1, FRÁGIL) | 110 e 150 | **BATE** |
| Yazalaque 09h30 | NÍVEL | *aceita* 195..215 (5) | 170..210 | DISCORDA |

*(largura na convenção declarada: contagem de pisos da grade, inclusiva.)*

**A única linha que BATE é o que dá crédito às outras onze.** Uma reprodução que só pode concordar
não prova nada; uma que só pode discordar está quebrada.

## Os três achados que este plano acrescentou, e que ninguém tinha

1. **Concordância entre as duas escalas não é evidência de acerto em campo nenhum.** Três das
   quatro leituras de nível aceitas-e-erradas são `ACEITA-2-ESCALAS`. O M-H tinha medido isso na
   adena e explicado por um sósia gramatical adjacente (a L-Coin); **no nível não há sósia** — as
   duas escalas leram o mesmo dígito errado (`69` por `67`, `65` por `69`, `37` por `67`).
   *Consequência:* quem exibir o campo `escalas` do `ValorDaRenda` não pode escrever "conferido" ao
   lado do `2`.

2. **As bandas se movem com o cenário, e muito.** Entre 00h45 e 09h30, com outro cenário atrás da
   barra semitransparente, a banda do EXP da Faerlina vai de `140..170` para `160..180` — elas mal
   se tocam. A do nível da Yazalaque vai de `170..215` para `195..215`. A intuição do M-E (*"a banda
   muda com o lugar de farm"*) agora tem dois cenários reais e 8h30 de distância.

3. **A abstenção por gramática esconde concordância no erro.** Nos três casos do EXP aceitos-e-
   errados, a 3x leu os **mesmos dígitos errados** que a 2x (`EXP 35.28450/2` contra
   `EXP 35.2845%`) e abstém por gramática, não por desacordo. O cruzamento não tem como saber a
   diferença. É o limite dele, e fica registrado aqui em vez de virar surpresa no `01-04`.

## Deviations from Plan

### 1. [Rule 3 — Ambiente] O `.venv` continua sem `pytest`, e o comando do plano não roda como escrito

O plano manda `python -m pytest tests/test_medir_a_renda.py -q`. O `.venv` de produção tem OCR e
**não** tem pytest; o Python global tem pytest e **não** tem as bindings de OCR. É o mesmo achado
que o `01-01` registrou, e a mesma ponte resolve, **sem instalar nada** no ambiente do usuário:

    PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest tests/test_medir_a_renda.py -q

Este arquivo de teste é o caso feliz dessa história: ele **não usa OCR**, então roda igual nos dois.
Medido: `55 passed`, **0 skipped**, no Python global puro *e* com a ponte.

Para **rodar a ferramenta** a ponte é o outro lado: `.venv/Scripts/python.exe` com `PYTHONPATH` na
raiz, que é o comando que produziu todos os números acima.

### 2. [Rule 2 — Ruído que esconde o relatório] O `warning` de recusa da produção é silenciado NA BANCADA

`renda_leitura._recusar` grava um `warning` por recusa, deliberadamente sem limitação de repetição,
porque o log rotativo é a única forense pós-farm deste projeto. Numa varredura de 31 pisos × 3
regiões × 4 frames isso são centenas de linhas idênticas em `stderr`, **intercaladas com a saída** —
medido na primeira execução, e o relatório ficou ilegível.

`calar_o_log_de_recusa_da_producao()` põe o logger `l2scanner.renda_leitura` em `ERROR`, **só dentro
da ferramenta**. Nenhuma informação se perde: o relatório imprime, para cada piso, os dois textos
crus entre `>>><<<`, os dois inteiros, o desfecho, o valor e o veredicto — com gravação, frame e
personagem na linha. Isso é estritamente mais que o `warning` calado, e com procedência. A produção
grava exatamente o que gravava.

### 3. [Escopo] A gramática do nível e da adena veio de `mercado_leitura`, e isso está dito em voz alta

`renda_leitura` tem a gramática do EXP e mais nenhuma — a do nível nasce no `01-04` e a da adena por
glifo no `01-05`. Escrever uma gramática nova aqui seria a ferramenta medindo a si mesma. O censo
usa `mercado_leitura.numero_valido` + `inteiro_de_quantidade`, que é **exatamente** a gramática que
o M-G mediu em campo quando escreveu que `106.020` e `91` passam. A fronteira está escrita na
docstring da ferramenta e num teste (`test_o_EXP_usa_a_gramatica_DE_PRODUCAO_e_nao_a_de_inteiro`).

Uma decisão dentro dessa: **ambiguidade recusa**, na mesma disciplina de `decimos_de_milesimo`. Isso
pode divergir do M-G, então o relatório **conta e imprime** quantas leituras foram recusadas por
ambiguidade, para que o confundidor fique visível em vez de escondido.

## Como cada critério de aceitação foi verificado

| critério | resultado |
| -------- | --------- |
| `pytest tests/test_medir_a_renda.py -q` = 0 no Python global, sem skip | **55 passed, 0 skipped** |
| relatório 1 com `--personagem Faerlina` sai 0, imprime linha por piso, banda com LARGURA e extremos, e a comparação com o M-E | exit 0; três regiões, 31 pisos cada, bandas e veredictos impressos |
| o mesmo com `--personagem Yazalaque` produz bandas do OUTRO personagem | exit 0; nível `236,750` contra `246,736`, bandas diferentes |
| banda de largura 1 sai marcada como FRÁGIL, com a razão; e há teste puro | Yazalaque ADENA `145` sai `*** FRAGIL ***`; `TestABandaFragil` (5 testes) |
| a grade anda de 5 em 5, com teste e mensagem citando o 155 | `test_o_passo_de_10_e_RECUSADO_com_o_numero_na_mensagem` + o controle negativo |
| a adena sai rotulada CAMINHO ABANDONADO com o LEIT-09, e a quinta contagem sai só para ela | rótulo impresso nos dois relatórios; quinta contagem impressa para os três campos, e a linha da adena é `5/10 (50,0%)` |
| relatório 2 sobre `recordings` sai 0 e imprime as quatro contagens COM denominador + a lista da discordância | exit 0; `124` por campo; dois frames de discordância listados com os dois valores |
| `grep -c "_cruzar_as_escalas"` (fora de comentário) ≥ 1, sem segunda partição | **7** |
| frames pulados contados e impressos; pasta sem frame compatível sai 0 com mensagem | 2379 pulados impressos por motivo; pasta vazia → exit 0 com a mensagem, sem traceback |
| `grep -rc "recordings" tests/test_medir_a_renda.py` = 0 | **0** |
| `grep -c "def "` (fora de comentário) ≥ 6 | **30** |
| `01-MEDICOES.md` existe com ≥ 7 seções de topo | **10** |
| `grep -cE "20[0-9]{2}-..-.."` em `tools/medir_a_renda.py` ≥ 1 | **4**, e o bloco diz "resultado de **UMA** rodada" |
| `git diff --stat l2scanner/ requirements.txt` vazio | **vazio** |
| suíte completa não quebrou nenhum vizinho | **4925 passed, 24 skipped** (sem `test_agenda.py`) |
| `ruff check` nos dois arquivos novos | `All checks passed!` |

## Known Stubs

Nenhum. Todo caminho desta bancada ou lê pixel real e imprime com procedência, ou diz que pulou e
por quê. Nenhuma função devolve valor fixo, lista vazia ou placeholder.

Duas ausências **deliberadas**, escritas para não parecerem esquecimento:

- **O caminho de glifo não é medido.** Ele nasce no `01-03` (o cortador) e no `01-04`. Medi-lo aqui
  obrigaria esta bancada a esperar por eles. Escrito na docstring e no rodapé do relatório 2.
- **A banda CERTA não existe onde não há verdade de campo escrita.** Ela sai como *"não mensurável"*
  e nunca como erro — tratar ausência de gabarito como erro inflaria a taxa pelo lado errado.

## Deferred Issues (fora do escopo deste plano)

- **`tests/test_agenda.py` continua abortando a sessão do pytest de forma intermitente**
  (pré-existente, documentado pelo `01-01`, sem relação com esta fase). A suíte completa foi rodada
  com ele deselecionado, conforme instrução.
- **A taxa de discordância do EXP e da adena é `0/124` com quatro frames.** Isso não diz que ela é
  zero na população. Mais gravações de renda a movem, e a bancada roda por comando exatamente para
  isso — está registrado em "O que fica em aberto" no `01-MEDICOES.md`.

## O que a onda 3 herda

- **A recusa por discordância fica**, e agora por medição: `2/124` no nível, com os dois casos sendo
  o valor que a concordância aceitou noutro frame. O `01-04` a mantém sem discussão.
- **O `escalas=2` não é selo de qualidade em campo nenhum.** Quem exibir a renda não escreve
  "conferido" ao lado do `2`.
- **O LEIT-09 tem denominador**: 50% das leituras aceitas da adena por OCR estavam erradas, e num
  cenário a banda certa tem largura zero.
- **As bandas de piso mudam com o cenário**, então `largura_da_banda` é o campo que diz ao usuário
  quanta folga ele tem antes de precisar recalibrar — e uma largura 1 gravada é um pedido de
  recalibração, não uma calibração.
- **A bancada roda por comando** e pode ser refeita no dia em que o usuário mudar de resolução, de
  gamma ou de skin — inclusive contra este próprio documento.

## Self-Check: PASSED

Arquivos conferidos em disco: `tools/medir_a_renda.py`, `tests/test_medir_a_renda.py`,
`.planning/workstreams/renda/phases/01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa/01-MEDICOES.md`.

Commits conferidos em `git log`: `2823c0a`, `cb87253`.
