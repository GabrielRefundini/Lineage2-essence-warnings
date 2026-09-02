# Medições do `01-02` — os veredictos: cinco citados, um medido, e as refutações

**Data da rodada: 2026-09-02.** Uma rodada só. Todo número desta página é o resultado de **uma**
execução da bancada contra as quatro fixtures de campo; ele pode ser refutado por outra rodada, e
é para isso que a bancada existe por comando em vez de por prosa.

## Como esta rodada foi feita — a procedência de tudo que está escrito abaixo

Ferramenta: `tools/medir_a_renda.py` (nasce neste plano). Calibração: a fixture versionada
`tests/fixtures/renda/calibracao_de_fixture.json`, que carrega os retângulos que o M-O produziu —
`barra_esquerda` (EXP) `0,1368 520x24`, `barra_direita` (ADENA) `1540,1358 160x34`, e `nivel`
`246,736 30x20` na Faerlina contra `236,750 30x20` na Yazalaque.

Gravações varridas (as duas únicas com renda; **gitignored**, por isso a ferramenta as lê e nenhum
teste as abre):

    20260902-004500-renda-duas-instancias/frame_000000_faerlina.png    1720x1392
    20260902-004500-renda-duas-instancias/frame_000001_yazalaque.png   1720x1392
    20260902-093000-renda-segundo-cenario/frame_faerlina.png           1720x1392
    20260902-093000-renda-segundo-cenario/frame_yazalaque.png          1720x1392

Comandos exatos:

    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py --relatorio 1 \
        --gravacoes recordings/20260902-004500-renda-duas-instancias --personagem Faerlina
    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py --relatorio 1 \
        --gravacoes recordings/20260902-004500-renda-duas-instancias --personagem Yazalaque
    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py --relatorio 1 \
        --gravacoes recordings/20260902-093000-renda-segundo-cenario
    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py --relatorio 2 \
        --gravacoes recordings

Grade: **100 a 250, de 5 em 5**, 31 pisos. Nunca de 10 em 10 — a razão está no M-G e está repetida
na refutação 11 abaixo. Frames pulados no lote inteiro: **2379**, todos por *sem personagem no
nome do arquivo*; zero por forma incompatível, zero por calibração ausente, zero ilegíveis em
disco.

**Duas convenções, declaradas antes de qualquer número, porque um pixel sem convenção já custou
uma refutação a esta fase (M-P):**

| grandeza | convenção desta página | onde mais ela aparece |
|---|---|---|
| **largura de banda de piso** | **contagem de PISOS DA GRADE, INCLUSIVA nos dois extremos**: `180..190` com passo 5 vale **3** | é a mesma de `largura_da_banda` no `calibration.json` |
| vão da mesma banda, em níveis de V | `fim - inicio`, EXCLUSIVO: a mesma banda vale **10** | impresso ao lado, entre parênteses, em toda linha de banda |
| largura de run de glifo | **não é usada nesta página** — quando for, é `fim - inicio` (EXCLUSIVA), a de `larguras_de_molde` | o `01-MEDICOES-DE-CAMPO.md` relata glifos na convenção **inclusiva** (5/6/7), o código na exclusiva (4/5/6) |

## Pergunta 1 — A altura de glifo da barra é a dos moldes do mercado?

**Resposta: a pergunta é moot, e não foi remedida aqui.** Ela só tinha consequência para o caminho
de moldes de glifo a partir do mercado, e esse caminho já estava morto para a barra antes desta
rodada.

Achado que a respondeu: **item M10 do `01-01-PLAN.md`** (um run de 519 px — a segmentação não
separa nada) e a **pesquisa (c3)** para o nível. E o **M-I** do Adendo respondeu a versão útil
dela: os moldes do mercado não transferem. O **M-K** corrigiu o número (o glifo é 5x10, não 17 de
altura — o 17 vinha do ícone dentro do recorte) sem derrubar o veredicto.

Consequência: CTX-1 ficou com OCR mascarado; os moldes da barra são **construídos** pelo cortador
do `01-03`, e a guarda de altura dele se compara contra **10**, nunca contra 17.

## Pergunta 2 — A tinta da barra é acromática?

**Resposta: moot pelo mesmo motivo, e também não foi remedida.** Ela importava porque o seletor de
moldes recusa tinta fora da curva; sem caminho de moldes herdados do mercado, não há seletor a
satisfazer.

Achado que a respondeu: **M10 do `01-01-PLAN.md`** e a **pesquisa (c3)**.

## Pergunta 3 — Existem dígitos nos pixels à direita que o spike nunca capturou?

**Resposta: sim, existiam — e o retângulo que os cortava já caiu duas vezes.** O recorte da direita
devolve `13.160.684` e `1.696.020`, que são exatamente a verdade de campo dos dois personagens; um
recorte que cortasse dígito não produziria o número inteiro.

Achado que a respondeu: a **tabela de verdade de campo** de `01-MEDICOES-DE-CAMPO.md`, e depois o
**M-N/M-O/M-Q**, que derrubaram `1500,1360 200x32` (medido numa fixture cuja L-Coin era curta) em
favor de `1540,1358 160x34` — o único que sobrevive às **quatro** fixtures.

A guarda contra o corte continua sendo o `recortar` do `01-01`, que **recusa** retângulo que não
cabe em vez de encurtar (M12).

**Esta rodada acrescenta um dado a essa pergunta, e ele é ruim para o OCR:** com o retângulo
corrigido, a adena da Faerlina de 09h30 (`20260902-093000-renda-segundo-cenario/frame_faerlina.png`)
não sai correta em **nenhum** dos 31 pisos — banda certa de largura **0**. O retângulo está certo;
o leitor é que não serve. Ver a pergunta 6 e a refutação 6.

## Pergunta 4 — Qual a banda útil de piso de brilho de cada região, e as três coincidem?

**Resposta: elas não coincidem, e por isso o piso é por região e por personagem.** O piso do nível
(190+) e o piso da adena por OCR (150) não têm interseção nenhuma; um campo `renda_piso_de_brilho`
único é impossível.

Achado que a respondeu: **M-E** de `01-MEDICOES-DE-CAMPO.md`. Nada disso foi remedido aqui — a
resposta é dele.

Consequência: virou o **LEIT-08**, e o esquema do `01-01` já nasceu com um `piso_de_brilho` dentro
de **cada** região de **cada** personagem, mais um `largura_da_banda` opcional ao lado.

**A tabela de bandas do M-E foi REPRODUZIDA por código nesta rodada, e ela não sobreviveu.** Isso é
um artefato separado desta pergunta, e está na seção "A varredura de piso reproduzida por código"
abaixo. A resposta da pergunta 4 — *não coincidem, um piso por região* — sai **reforçada** pela
reprodução; o que caiu foram os números de cada banda.

## Pergunta 5 — O nível está em alguma gravação existente?

**Resposta: está, nas duas instâncias, com verdade de campo escrita — e a caça ao nível deixou de
ter objeto.**

Achado que a respondeu: **M-A** (as coordenadas do spike sobrevivem ao espaço da janela) e **M-F**
(a janela de status fica em lugar diferente em cada instância: `246,736` contra `236,750`, 14 px na
vertical e 10 na horizontal). Verdade de campo: **67** na Faerlina e **69** na Yazalaque.

Consequência: as duas ameaças do registro deste plano que existiam por causa de um relatório ao
vivo (`T-01-22`, input ao jogo; `T-01-23`, recortes gravados em disco) ficaram **sem componente**.
Elas seguem listadas no `01-02-PLAN.md` para que ninguém reintroduza o caminho sem reintroduzir as
guardas.

## Pergunta 6 — Com que frequência, com denominador, duas leituras de gramática VÁLIDA dos mesmos pixels produzem inteiros DIFERENTES?

**Resposta, medida: 2 em 124 no nível (1,6%), 0 em 124 no EXP, 0 em 124 na adena — e a guarda não
dorme, porque os dois casos que ela pegou são exatamente o valor errado que a concordância entre as
duas escalas ACEITOU em outro frame.**

Unidade do censo: `(gravação, frame, personagem, região, PISO)`. Cada piso da grade é uma leitura
dos **mesmos pixels** — 4 frames × 31 pisos = **124 por campo**. Um censo restrito ao piso já
calibrado teria denominador 4 e não mediria nada.

### Os quatro desfechos, com denominador

| campo | n | ACEITA-2-ESCALAS | ACEITA-1-ESCALA | RECUSA-ILEGÍVEL | **RECUSA-DISCORDÂNCIA** |
|---|---|---|---|---|---|
| `barra_esquerda` (EXP) | 124 | 21 (16,9%) | 11 (8,9%) | 92 (74,2%) | **0 (0,0%)** |
| `barra_direita` (ADENA) — *caminho abandonado, LEIT-09* | 124 | 1 (0,8%) | 10 (8,1%) | 113 (91,1%) | **0 (0,0%)** |
| `nivel` (NÍVEL) | 124 | 23 (18,5%) | 17 (13,7%) | 82 (66,1%) | **2 (1,6%)** |

### Os dois casos de discordância, nomeados

Cada um é uma fixture futura:

| gravação / frame | personagem | piso | 2x | 3x | cru |
|---|---|---|---|---|---|
| `20260902-093000-renda-segundo-cenario/frame_yazalaque.png` | Yazalaque | 175 | **65** | **69** | `>>>65-<<<` / `>>>69<<<` |
| `20260902-093000-renda-segundo-cenario/frame_yazalaque.png` | Yazalaque | 190 | **69** | **65** | `>>>69<<<` / `>>>65t<<<` |

**Este é o número que justifica a guarda, e ele se justifica por mais do que a taxa.** O valor
`65` não é ruído aleatório: ele é *o mesmo* valor que a regra do cruzamento **aceitou com as duas
escalas concordando** na gravação de 00h45, nos pisos 175 e 180 da Yazalaque. Quer dizer:

- num frame, `65` passou pela concordância e virou número gravado (errado — a verdade é `69`);
- noutro frame, nos mesmos pisos vizinhos, as escalas **discordaram** entre `65` e `69`, e a
  recusa por discordância pegou.

Uma guarda que pega o erro que a outra guarda deixa passar não é uma guarda que dorme. Ela custa
uma leitura de OCR por campo — orçada na tabela do `ocr.py` — e o dano que ela evita é um número
errado gravado para sempre. **Ela fica.**

### Quem sustentou o ACEITA-1-ESCALA — a assimetria é propriedade do campo, e não do frame

| campo | sustentado pela 2x | sustentado pela 3x |
|---|---|---|
| EXP | **11** | 0 |
| ADENA | 9 | 1 |
| NÍVEL | 2 | **15** |

A medição de campo tinha sugerido isto sem número (M-D: *"o nível da Faerlina só sai na 3x, a
adena só na 2x"*). Agora está com denominador: **o nível é da 3x e o EXP e a adena são da 2x**, e
nenhum dos dois é acidente de frame. Um curto-circuito na escala barata calaria o nível
inteiro — que é exatamente o desenho que o `01-01` já corrigiu.

### A quinta contagem — de todas as leituras ACEITAS, quantas estavam ERRADAS

Só onde há verdade de campo escrita. Ausência de gabarito conta como **não mensurável**, e nunca
como erro.

| campo | aceitas com gabarito | **erradas** | taxa |
|---|---|---|---|
| EXP | 27 | 3 | **11,1%** |
| ADENA | 10 | 5 | **50,0%** |
| NÍVEL | 18 | 4 | **22,2%** |

Cada uma, nomeada:

| campo | gravação / frame | personagem | piso | leu | verdade | desfecho |
|---|---|---|---|---|---|---|
| EXP | `093000/frame_yazalaque.png` | Yazalaque | 170 | 352845 | 852845 | ACEITA-1-ESCALA |
| EXP | `093000/frame_yazalaque.png` | Yazalaque | 175 | 952845 | 852845 | ACEITA-1-ESCALA |
| EXP | `093000/frame_yazalaque.png` | Yazalaque | 180 | 352945 | 852845 | ACEITA-1-ESCALA |
| ADENA | `004500/frame_000000_faerlina.png` | Faerlina | 100 | 13 | 13160684 | **ACEITA-2-ESCALAS** |
| ADENA | `004500/frame_000000_faerlina.png` | Faerlina | 170 | 13160634 | 13160684 | ACEITA-1-ESCALA |
| ADENA | `004500/frame_000000_faerlina.png` | Faerlina | 190 | 3 | 13160684 | ACEITA-1-ESCALA |
| ADENA | `004500/frame_000001_yazalaque.png` | Yazalaque | 195 | 2 | 1696020 | ACEITA-1-ESCALA |
| ADENA | `093000/frame_faerlina.png` | Faerlina | 115 | 151 | 15134779 | ACEITA-1-ESCALA |
| NÍVEL | `004500/frame_000000_faerlina.png` | Faerlina | 185 | 69 | 67 | ACEITA-1-ESCALA |
| NÍVEL | `004500/frame_000000_faerlina.png` | Faerlina | 220 | 37 | 67 | **ACEITA-2-ESCALAS** |
| NÍVEL | `004500/frame_000001_yazalaque.png` | Yazalaque | 175 | 65 | 69 | **ACEITA-2-ESCALAS** |
| NÍVEL | `004500/frame_000001_yazalaque.png` | Yazalaque | 180 | 65 | 69 | **ACEITA-2-ESCALAS** |

**A adena com 50% de erro entre as aceitas é o M-G com denominador**, e ele **confirma** o Adendo:
metade de tudo que o caminho de OCR aceitou naquele campo estava errado. Somado à banda certa de
largura **0** na Faerlina de 09h30, o LEIT-09 não precisa de mais argumento.

**E há um achado novo, que o Adendo não tinha, e ele é caro:** três das quatro leituras de nível
aceitas-e-erradas vieram de **ACEITA-2-ESCALAS**. O M-H tinha medido que concordância não é
evidência de acerto **na adena**, e explicou por um sósia gramatical adjacente (a L-Coin). No
nível não há sósia: as duas escalas simplesmente leram o **mesmo dígito errado** — `69` em vez de
`67`, `65` em vez de `69`, `37` em vez de `67`. Concordância entre 2x e 3x não é evidência de
acerto em campo nenhum, e agora isso está medido nos dois.

**E uma nota de método que muda como se lê o EXP acima.** Nos três casos do EXP a 3x leu os
**mesmos dígitos errados** que a 2x (`EXP 35.28450/2` contra `EXP 35.2845%`) e abstém por
**gramática**, não por desacordo. Ou seja: a abstenção por gramática **esconde uma concordância no
erro**. O cruzamento não tem como saber a diferença, e é mais uma razão para a taxa de
discordância não ser a única guarda do EXP.

## A varredura de piso reproduzida por código — e o que ela derruba

Este é o segundo produto da rodada, e o valor dele está em ele poder falhar. **Falhou em 11 das 12
comparações.**

### 2026-09-02, 00h45 (`20260902-004500-renda-duas-instancias`)

| personagem | região | BANDA ACEITA | BANDA CERTA | M-E (a olho, 10 em 10) | veredicto |
|---|---|---|---|---|---|
| Faerlina | EXP | 140..170 (7) | 140..170 (7) | 150..170 | **DISCORDA** |
| Faerlina | ADENA | 150..160 (3) | 150..160 (3) | 150 (ponto) | **DISCORDA** |
| Faerlina | NÍVEL | 185..220 (8) | 190..215 (6) | 190..220 | **DISCORDA** |
| Yazalaque | EXP | 125..170 (10) | 125..170 (10) | 130..170 | **DISCORDA** |
| Yazalaque | ADENA | 145 (1, **FRÁGIL**) | 145 (1, **FRÁGIL**) | 110 e 150 | **DISCORDA** |
| Yazalaque | NÍVEL | 170..215 (10) | 185..215 (7) | 170..210 | **DISCORDA** |

### 2026-09-02, 09h30 (`20260902-093000-renda-segundo-cenario`)

| personagem | região | BANDA ACEITA | BANDA CERTA | M-E | veredicto |
|---|---|---|---|---|---|
| Faerlina | EXP | 160..180 (5) | sem gabarito | 150..170 | **DISCORDA** |
| Faerlina | ADENA | 115 (1, **FRÁGIL**) | **nenhum piso (0)** | 150 | **DISCORDA** |
| Faerlina | NÍVEL | 165..220 (12) | sem gabarito | 190..220 | **DISCORDA** |
| Yazalaque | EXP | 135..180 (10) | 135..165 (7) | 130..170 | **DISCORDA** |
| Yazalaque | ADENA | 110 (1, **FRÁGIL**) | sem gabarito | 110 e 150 | **BATE** |
| Yazalaque | NÍVEL | 195..215 (5) | sem gabarito | 170..210 | **DISCORDA** |

*(largura entre parênteses, na convenção declarada no topo: contagem de pisos da grade, inclusiva.)*

**A única linha que BATE é o que dá crédito às outras onze.** Uma reprodução que só pode concordar
não prova nada; uma que só pode discordar está quebrada. Esta faz as duas coisas.

Quatro coisas caem daqui, e três delas são novas:

1. **A banda ACEITA e a banda CERTA não são a mesma coisa, e a diferença é onde mora o perigo.** No
   nível da Faerlina de 00h45 elas diferem em dois pisos — `185` e `220` são aceitos e errados. Um
   calibrador que propusesse o centro da banda ACEITA proporia `202`, dentro da banda certa por
   sorte; um que propusesse o extremo proporia `220`, que lê `37`.
2. **As bandas se MOVEM com o cenário, e muito.** A banda certa do EXP da Faerlina é `140..170` às
   00h45; a banda aceita às 09h30 é `160..180`. Elas mal se tocam. A do nível da Yazalaque vai de
   `170..215` para `195..215`. Isso confirma a intuição do M-E (*"a banda muda com o lugar de
   farm"*) com dois cenários reais e 8h30 de distância — e é o argumento mais forte a favor de a
   calibração ser refeita quando o usuário troca de mapa, e não uma vez na vida.
3. **A banda frágil não sumiu quando a adena saiu do OCR: ela ficou.** Três das quatro medições de
   adena por OCR têm largura **1**. E a Faerlina de 09h30 tem largura **0** — o caso que a marca de
   frágil não cobre, porque não há banda nenhuma para marcar.
4. **A tabela do M-E é do retângulo antigo.** Boa parte da discordância na linha da adena se explica
   por isso: o M-E mediu com `1500,1360 200x32`, que o M-O derrubou. Isso **não** salva as linhas
   do EXP e do nível, que usam os mesmos retângulos nas duas medições e discordam do mesmo jeito.

## Refutações — o que documento nenhum apagou, e o número que derrubou cada uma

Formato da pesquisa: o que o documento dizia, o número que o derrubou, e a consequência para quem
vem depois. **Nenhuma afirmação foi removida do documento de origem por este plano.**

### As cinco do corpo do documento de campo

**1. *"a leitura da adena já quase funciona"* no recorte cru** — `ROADMAP.md`, premissa do LEIT-03.
Derrubada duas vezes: pelo **M7** do `01-01` e, com fundo de grama clara, pelo **M-E**, onde o cru
devolve `''` nas duas escalas. *Consequência:* a máscara é obrigatória, não opcional.

**2. *"os moldes de glifo são o caminho do nível"*** — `CONTEXT.md`. Derrubada pela **pesquisa (c3)**
e pelo **M10**. *Consequência:* o nível fica no OCR mascarado, sem plano B — e é por isso que a
pergunta 6 vale mais para ele, e não menos.

**3. *"as duas leituras têm que dar o mesmo número; divergiram → recusa"*** — `CONTEXT.md`, Área 2.
Derrubada pelo **M-D**. É a refutação mais cara da fase: a regra escrita recusaria o nível da
Faerlina e a adena da Faerlina **para sempre**, e recusar 100% das amostras é o mesmo que não ter
medidor. *Consequência:* a regra é por **abstenção**, e `_cruzar_as_escalas` carrega a refutação
inteira na docstring.

**4. *"um piso de brilho para a barra e um para o nível"*** — `01-01-PLAN.md`, item M9. Derrubada
pelo **M-E**: são três, um por região, porque as bandas não têm interseção. *Consequência:*
LEIT-08, e o `piso_de_brilho` dentro de cada região no esquema.

**5. *"uma calibração serve às duas instâncias"*** — pressuposto de todos os documentos até
2026-09-02. Derrubada pelo **M-F** (14 px de diferença na vertical). *Consequência:* LEIT-07, e o
acessor `renda_do_personagem`, que devolve a entrada dele ou **nada** — nunca a do vizinho.

### As três do Adendo

**6. *"o Windows OCR devolve a adena"*** — `ROADMAP.md`, a segunda metade da premissa do LEIT-03,
depois de o M-E já ter derrubado a primeira. Derrubada pelo **M-G** (a regra da abstenção aceita
`106.020` e `91`) e pelo **M-H** (173 concordâncias da Faerlina, 173 lendo a L-Coin).
**Confirmada com denominador nesta rodada:** **5 de 10** leituras aceitas da adena estavam erradas
(50,0%), e na Faerlina de 09h30 a banda certa tem largura **0** em 31 pisos. *Consequência:* a
adena é lida por **glifo** — LEIT-09.

**7. *"os moldes do mercado podem servir para a barra"*** — a primeira pergunta em aberto que a
pesquisa deixou. Derrubada pelo **M-I**, e o número dela corrigido pelo **M-K**: o glifo da barra é
**5x10**, e os moldes do mercado são **4x9**. *Consequência:* o `01-03` ganhou uma tarefa de cortar
moldes, e a guarda de altura dela se compara contra **10** — uma guarda escrita contra o `17`
contaminado recusaria todo molde legítimo, e o modo de falha seria um cortador que nunca corta.

**8. *"a banda útil da adena tem largura 1 e isso é sorte"*** — M-E, e este próprio plano repetia o
exemplo. **Parcialmente derrubada** pelo **M-J**: era verdade no caminho de OCR, e a banda de glifo
do mesmo campo é `180..190`, larga. *Consequência:* o aviso de banda frágil continua valendo para o
EXP e o nível; o que caiu foi o exemplo canônico dele.

### As quatro que ESTA rodada acrescentou

**9. *"a banda útil da adena da Faerlina é `150`, um ponto"*** — `01-MEDICOES-DE-CAMPO.md`, M-E.
Derrubada por esta rodada: com o retângulo corrigido do M-O, ela é `150..160`, **largura 3**, nas
mesmas fixtures. O M-E mediu com `1500,1360 200x32`, que o M-N/M-O/M-Q refutaram.
*Consequência:* o exemplo canônico de banda de largura 1 no caminho de OCR deixou de ser a
Faerlina de 00h45. Ele continua existindo — a **Yazalaque** de 00h45 (`145`, largura 1) e as duas
de 09h30 (`115` e `110`, largura 1) —, então o aviso de fragilidade **não** cai; só troca de dono.
Uma refutação que derruba o exemplo e não a regra tem de dizer as duas coisas.

**10. *"concordância entre as duas escalas é evidência de acerto, exceto na adena onde há sósia
gramatical"*** — implícito no **M-H**, que explicou o problema da adena pela L-Coin adjacente.
Derrubada por esta rodada **no nível**: **3 das 4** leituras de nível aceitas-e-erradas são
`ACEITA-2-ESCALAS` (`69` no lugar de `67`, `65` no lugar de `69` duas vezes, `37` no lugar de `67`).
Ali não há sósia nenhum — as duas escalas leram o mesmo dígito errado. *Consequência:* nenhum campo
pode tratar `escalas=2` como selo de qualidade. O campo `escalas` do `ValorDaRenda` continua sendo
o custo se anunciando, e não uma nota de confiança — e quem for exibi-lo não pode escrever
"conferido" ao lado do `2`.

**11. *"a taxa de discordância pode vir zero, e nesse caso a guarda dorme"*** — este próprio plano,
`01-02-PLAN.md`, na Tarefa 2. **Não veio zero**: `2 / 124` no nível (1,6%). E os dois casos são o
valor `65`, que é exatamente o que a concordância entre as duas escalas **aceitou** no outro
frame. *Consequência:* a recusa por discordância deixa de precisar do argumento "custa pouco e o
dano é grande" — ela pegou, nesta árvore, o erro que a outra guarda deixou passar. O `01-04` a
mantém sem discussão.

**12. *"a banda calibrada num cenário vale no seguinte"*** — pressuposto de todo campo
`piso_de_brilho` gravado uma vez no `calibration.json`. Derrubada por esta rodada: entre 00h45 e
09h30, com 8h30 e outro cenário atrás da barra semitransparente, a banda do EXP da Faerlina vai de
`140..170` para `160..180` e a do nível da Yazalaque de `170..215` para `195..215`.
*Consequência:* o `largura_da_banda` que o esquema já guarda é o campo que dá para o usuário a
noção de quanta folga ele tem antes de precisar recalibrar — e uma largura 1 gravada é um pedido de
recalibração na próxima troca de mapa, não uma calibração.

---

## O que fica em aberto, e onde

- **A taxa de discordância do EXP e da adena é `0/124`.** Isso não diz que ela é zero na população;
  diz que quatro frames em 31 pisos não produziram nenhuma. Mais frames de renda a movem, e a
  bancada roda por comando exatamente para isso.
- **A abstenção por gramática esconde concordância no erro** (os três casos do EXP acima). Isso não
  é uma falha do cruzamento — é o limite dele, e ele fica registrado aqui em vez de virar surpresa
  no `01-04`.
- **O caminho de glifo não foi medido**, por decisão: ele nasce no `01-03` e no `01-04`. Quando
  nascer, esta mesma bancada é onde ele ganha denominador contra o caminho de OCR.
