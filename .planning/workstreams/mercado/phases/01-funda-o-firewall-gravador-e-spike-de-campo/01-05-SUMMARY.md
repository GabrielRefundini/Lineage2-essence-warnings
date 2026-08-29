---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 05
subsystem: calibracao-do-mercado
tags: [glifos, ocr-por-template, calibracao, gap-closure, FUND-03]
status: checkpoint
gap_closure: true
closes_gap: G-01
requires:
  - phase: 01-04
    provides: "calibrar_mercado.py, o par ancoras_para/de_calibracao, molde_para/de_hex, ResultadoDaConfusao"
  - phase: 01-03
    provides: "SPIKE-RESPOSTAS.md validado — a virgula como separador de milhar E decimal, e o sufixo como desambiguador"
provides:
  - "l2scanner/calibrar_mercado.segmentar_glifos: segmentacao por projecao de coluna sobre a mascara de brilho, com a faixa de linhas COMPARTILHADA na assinatura"
  - "l2scanner/calibrar_mercado.matriz_de_confusao_de_glifos: matriz propria, mascara binaria, alinhamento por PREENCHIMENTO, par incalculavel contado a parte"
  - "l2scanner/calibrar_mercado.COLISAO_MAXIMA_ENTRE_GLIFOS: constante SEPARADA da de templates, com as tres convencoes medidas na docstring"
  - "l2scanner/calibrar_mercado.cortar_glifos: o laco interativo com conferencia de CONTAGEM contra o rotulo digitado"
  - "l2scanner/calibrar_mercado.fundir_glifos: fusao por rotulo (CR-04) — o corte novo vence, o ausente e preservado"
  - "l2scanner/calibrar_mercado.VALOR_MINIMO_DO_SUFIXO + recortar_sufixo: piso de brilho PROPRIO das palavras de sufixo, medido"
  - "l2scanner/calibrar_mercado --so-digitos: corte isolado sobre outro frame, sem refazer ancoras e grade"
  - "l2scanner/mercado_visao.glifos_para/de_calibracao: empacotamento com guard de CONJUNTO (altura dominante dos glifos de um caractere)"
  - "l2scanner/calibracao.mercado_limiar_de_glifo: chave opcional via .get, faixa (0,1]; VERSAO_DO_ESQUEMA segue 2"
  - "tests/fixtures/mercado/glifos_precos_f010.png + glifos_unitario_f010.png: os onze glifos reais, commitados"
  - "l2scanner/mercado_geometria.py (DESVIO): localizar_o_titulo, medir_a_grade, ancora_deslocada — a grade e as ancoras MEDIDAS nos pixels, sem mouse"
  - "l2scanner/calibrar._selecionar_regiao(sugestao=None) (DESVIO): retangulo pre-desenhado, ENTER aceita; padrao None preserva a party byte a byte"
  - "l2scanner/calibrar_mercado.sugerir_a_coluna_de_preco (DESVIO): um retangulo por linha em volta do numero e da palavra de moeda"
  - "l2scanner/calibrar_mercado.propor_rotulo (DESVIO): a leitura proposta pelos glifos ja certificados, com piso 0.80 e margem 0.12 medidos"
  - "l2scanner/calibrar_mercado._avisar_divergencia_da_grade (DESVIO): informa a divergencia entre o desenhado e o medido, e NUNCA recusa"
affects: [fase 2 LEIT-02 leitura de precos por template-por-digito]
tech-stack:
  added: []
  patterns:
    - "conjunto fechado + correlacao de posicao unica (identidade.py), aplicado glifo a glifo"
    - "convencao de recorte DECLARADA na assinatura, para o numero de matriz ser reproduzivel"
    - "incalculabilidade por PRE-CONDICOES re-checadas, nunca por comparacao do score a 0.0"
    - "a ferramenta PROPOE e o humano CONFIRMA: parametro opcional com padrao que preserva o caminho antigo byte a byte"
    - "deteccao de faixa por TRECHOS DE NIVEL CONSTANTE, e nao por derivada — a derivada escolhe o lado errado da borda quando o contraste e assimetrico"
key-files:
  created:
    - tests/test_mercado_glifos.py
    - tests/fixtures/mercado/glifos_precos_f010.png
    - tests/fixtures/mercado/glifos_unitario_f010.png
    - l2scanner/mercado_geometria.py
    - tests/test_sugestao_de_calibracao.py
  modified:
    - l2scanner/calibrar_mercado.py
    - l2scanner/calibrar.py
    - l2scanner/mercado_visao.py
    - l2scanner/calibracao.py
    - calibrar-mercado.bat
    - tests/test_calibrar_mercado.py
    - .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/01-04-SUMMARY.md
decisions:
  - "A representacao dos moldes de glifo e a MASCARA BINARIA, nao o cinza: ela vence nas TRES convencoes de recorte medidas, por 0.10 a 0.13"
  - "O alinhamento da matriz dos glifos e por PREENCHIMENTO ate a maior caixa, nao por corte ao menor: cortar compara a virgula de 1 px contra a primeira coluna do digito (0.1918 contra 0.5000, medido)"
  - "As palavras de sufixo tem piso de brilho PROPRIO (V>120) — elas ficam INTEIRAS abaixo do piso de 180 dos digitos, com V maximo 173"
  - "O guard de altura do conjunto para nos glifos de UM caractere: a palavra sai com 8 px e o digito com 9, e exigir igualdade recusaria a calibracao correta"
  - "Duas matrizes de confusao, uma por confusao ALCANCAVEL: entre digitos e entre as duas palavras. Digito contra palavra nao e alcancavel"
  - "DESVIO: a ferramenta passa a PROPOR os cinco retangulos e a leitura do preco; o usuario confirma. Motivado por custo MEDIDO em campo (2026-08-29), nao por estetica"
  - "DESVIO: `_selecionar_regiao` ganha `sugestao` OPCIONAL em vez de um seletor novo. WR-08 foi recusado por temer a funcao compartilhada; o padrao `None` e a resposta a esse medo, com teste"
  - "DESVIO: a borda direita da grade e 1688 (onde a barra de rolagem comeca), e nao 1664 — 1664 e a borda do botao de carrinho da coluna Buy, medido"
  - "DESVIO: a proposta de LEITURA tem piso 0.80 e margem 0.12, e nao piso unico de 0.95: o mesmo digito casa 0.837 entre bandas de fundo diferentes"
metrics:
  duration: "~2h"
  completed: 2026-08-29
  tasks_completed: 2
  tasks_total: 3
actuals:
  tokens: 87000
  tasks: 2
  commits: 10
---

# Phase 01 Plano 05: Produtor dos Templates de Digito — Summary

Corte de glifos por projecao de coluna com convenção de recorte declarada, matriz de
confusão própria que recusa colisão e par incalculável, e o modo `--so-digitos` — dando
a `mercado_templates_de_digito` o produtor que nunca teve.

## ESTADO: AGUARDANDO O PORTÃO HUMANO (Task 3)

| Task | O que é | Estado |
|---|---|---|
| 1 | Segmentação, matriz dos glifos, par de empacotamento, fixtures resgatadas | **COMPLETA**, commits `d3dbcc2` (RED) + `f33883c` (GREEN) |
| — | Correção: piso de brilho próprio do sufixo (desvio medido, ver abaixo) | **COMPLETA**, commit `8608229` |
| 2 | Laço de corte, fusão, chave do limiar, `--so-digitos`, `.bat`, SUMMARY do 01-04 | **COMPLETA**, commits `710eca6` (RED) + `59fc6e8` (GREEN) |
| 3 | `checkpoint:human-action` `gate="blocking-human"` — a primeira mão humana no fluxo | **AGUARDANDO O USUÁRIO** |
| — | **DESVIO 2026-08-29**: a ferramenta passa a PROPOR os retângulos e a leitura — desbloqueia a Task 3, não a cumpre | **COMPLETO**, commits `ea699bb`, `a52f04b`, `0defa09`, `f5c3b1d` |

## A MATRIZ DE CONFUSÃO MEDIDA — com a convenção ao lado do número

**Convenção de recorte: LINHA-JUSTA COMPARTILHADA.** Uma única faixa de linhas por
retângulo marcado (`flatnonzero(mascara.any(axis=1))`, do primeiro ao último inclusive),
com cada glifo cortado nessa mesma faixa e nos seus próprios limites de coluna. Um número
de matriz sem a convenção ao lado não é reproduzível — foi exatamente assim que a primeira
versão deste plano errou.

Sobre os **11 glifos reais** (`0`-`9` e a vírgula) montados das duas fixtures commitadas,
55 pares:

| representação | pior par inter-classe | 2º pior | 3º pior | margem até 1.0 |
|---|---|---|---|---|
| tons de cinza nativo | **0.8434** (`0` x `8`) | 0.8101 (`5` x `6`) | 0.7797 (`3` x `8`) | 0.1566 |
| **máscara binária (V>180)** | **0.7171** (`5` x `6`) | 0.6952 (`0` x `8`) | 0.6549 (`3` x `5`) | 0.2829 |

**Diferença máscara↔cinza: 0.1263** — acima do piso de 0.08 que o critério exige. Todos os
números do plano reproduziram exatamente, incluindo o mínimo negativo do cinza (−0.1849),
que é a prova extra de que `0.0` não é piso e portanto não serve de sentinela.

**Os quatro zeros legítimos estão lá, e são MEDIÇÃO:** `(',','0')`, `(',','6')`, `(',','9')`
e `('0','7')` medem exatamente `0.0` na máscara, com desvios de 70.478 / 120.208 / 110.418 —
cinco ordens de grandeza acima do piso de `1e-6`. Nenhum é contado como não-mensurável, e o
conjunto real **APROVA**. Em tons de cinza não há zero nenhum: os quatro são fenômeno da
máscara. `,` x `2` mede **0.1918** com preenchimento contra **0.5000** com corte ao menor —
a regressão que o critério `< 0.30` existe para impedir.

**Geometria, idêntica ao medido:** faixa de **9 px** nas SETE marcações; dígitos de 4 px,
o `4` em 6 px, a vírgula em 1 px. Segmentação: **6, 4, 5, 4, 5, 4** e **4** — 7 de 7.

## O DESVIO QUE A EXECUÇÃO ENCONTROU (Rule 1)

**As palavras de sufixo não podiam ser cortadas com a máscara dos dígitos.** O plano
assumia que sim. Medido no `frame_000010`, na coluna à direita do preço:

| recorte | V máximo | V p99 | pixels com V>180 |
|---|---|---|---|
| preços (coluna Total) | 255 | 219 | 274 |
| `XM Coin` (ao lado) | **173** | 148 | **0** |

A palavra fica **inteira** abaixo do piso de 180 de `identidade.mascara_de_texto` — com o
piso dos dígitos, a máscara dela sai **vazia**, e um molde vazio não casa com nada. Marcar
a palavra teria produzido um molde nulo, descoberto só no fim de toda a marcação de mouse —
exatamente o modo de falha que este projeto vem matando.

`VALOR_MINIMO_DO_SUFIXO = 120` fica no meio de um platô largo e medido: qualquer piso entre
100 e 140 devolve a **mesma** faixa de 8 px e largura 35–36 px, idêntica nas seis linhas, e
o fundo não invade em nenhum deles (0 pixel de fundo acima do piso, em 4500 px de área sem
texto). Não há zona cinzenta a dividir: há um vale vazio.

**Consequência no guard de altura**, e é uma correção do meu próprio trabalho da Task 1: a
palavra sai com **8 px** e o dígito com **9 px**. Exigir a mesma altura dos dois grupos
**recusaria uma calibração correta** — o pior desfecho que um guard pode ter. O guard passa
a afirmar só onde tem evidência: os glifos de **um caractere**, que são também o conjunto de
onde um preço é lido. Um dígito transposto segue recusado, com teste
(`test_mas_um_DIGITO_de_altura_divergente_segue_recusado`).

Isto também motivou **duas matrizes** em vez de uma, pelas duas confusões realmente
alcançáveis: entre dígitos (troca o preço) e entre as duas palavras (inverte a convenção da
vírgula). Dígito contra palavra não é alcançável — moram em colunas diferentes e o leitor
sabe qual está lendo; e o alinhamento por preenchimento poria um dígito de 4 px dentro de
uma caixa de 35 px, medindo a área vazia em vez do desenho.

**Segundo desvio, menor:** `cortar_glifos` tinha `ler=input` como valor padrão, que amarra o
`input` existente no momento do import e ignora calado quem o substitua depois. Resolvido em
tempo de chamada.

## O DESVIO GRANDE — A FERRAMENTA PASSA A PROPOR (2026-08-29, Rule 2 + Rule 4 aprovada pelo usuário)

**Isto é um DESVIO explícito do `01-05-PLAN.md` como escrito, não uma tarefa dele.** A Task 3
do plano é um `checkpoint:human-action` que manda o usuário rodar a calibração com o mouse; ele
tentou, e o portão ficou bloqueado por um motivo que o plano não previa. O que segue foi
executado depois disso, sobre o plano parado.

### O custo medido em campo, que motivou a mudança

Em 2026-08-29 o usuário tentou o fluxo completo pela primeira vez e relatou, literalmente:
*"está muito difícil calibrar isso e é muito fácil eu errar na interpretação do que está sendo
pedido"*. Cada uma das cinco instruções em prosa gerou uma dúvida, e cada dúvida custou uma
ida e volta:

| instrução | a dúvida que ela gerou |
|---|---|
| "Marque a faixa de titulo 'XM Market'" | só o texto, ou a barra de título inteira? |
| "Marque a AREA DA LISTA inteira" | **o usuário incluiu o cabeçalho** — a grade saiu com **11 linhas** contra as 10 medidas para o layout adena |
| "Marque a PRIMEIRA LINHA" | largura inteira, ou só o preço? |
| "Marque UM numero da coluna de preco" | com o ícone da moeda? com o sufixo `XM Coin`? |
| "Marque a palavra 'XM Coin' INTEIRA" | uma ocorrência, ou todas? |

**O diagnóstico que importa não é ergonomia — é disciplina.** Em todo o resto deste código se
MEDE em vez de supor. A ferramenta de calibração fazia o oposto: pedia que o humano adivinhasse
o que uma frase queria dizer e aceitava o retângulo resultante em silêncio. O erro das 11 linhas
só foi pego porque `derivar_grade` tinha, por acaso, uma expectativa medida (`LINHAS_ESPERADAS`)
para aquele campo específico; os outros quatro retângulos não têm guarda nenhuma, e um deles
errado teria sido gravado sem uma palavra.

**E a capacidade já existia.** Um agente localizou a âncora de título por casamento de molde a
**0.9999** e derivou as bordas da grade do perfil vertical de intensidade, sem tocar no mouse.
Isso simplesmente não era oferecido ao usuário.

### Por que isso é `Rule 2` e não escopo novo

O plano-checker levantou exatamente esta ideia como **WR-08** e o planejador a recusou,
argumentando que exigiria mexer em `calibrar._selecionar_regiao`, compartilhada com a calibração
de party que funciona. Aquela cautela era razoável antes de haver medição do custo humano; agora
há, e o custo é maior. **A resolução mantém o caminho da party byte a byte**, que era a
preocupação inteira: o parâmetro é opcional e o padrão `None` reproduz o comportamento de hoje —
provado por `TestAPartyNaoMudou`.

### O que a medição reproduziu, e as duas divergências honestas

Tudo em `recordings/20260828-115700-calibragem/frame_000012.png` (1720x1392, aba Adena):

| grandeza | alvo dado | medido pela derivação | |
|---|---|---|---|
| âncora de título | 0.9999 em (1176, 362), 100x28 | **0.9999 em (1176, 362), 100x28** | ✅ |
| topo da grade (sem o cabeçalho) | 618 | **618** | ✅ |
| passo entre linhas | 45 | **45** | ✅ |
| linhas por página | 10 | **10** | ✅ |
| borda esquerda | 744 | **744** | ✅ |
| borda direita | 1664 | **1688** | ⚠️ divergência medida |
| `X` de fechar / seta de rolagem | +494,−10 e +494,+665, 60x60 | (1660, 352) e (1660, 1027) | ⚠️ empurrados |

**Divergência 1 — a borda direita é 1688, não 1664.** `x=1664` foi descrito como "o separador
vertical antes da barra de rolagem". Medido, ele não é: as colunas **1633 e 1664** leem 92 nas
duas bandas de fundo porque são as bordas **esquerda e direita do botão de carrinho** da coluna
`Buy`. O fundo alternado da linha (48 numa banda, 66 na outra) continua até **1687**, e a barra
de rolagem começa em **1688** — ali as duas bandas leem 48/48, sem alternância, que é
exatamente como ela é excluída sem precisar saber que existe. Cortar em 1664 amputaria a coluna
`Buy` da grade. A instrução impressa pela própria ferramenta já dizia *"de preferência pare
antes da barra de rolagem"*; 1688 é essa intenção, medida.

**Divergência 2 — `x=744` reproduz, mas por outra evidência.** A coluna 744 lê 48 nas DUAS
bandas (não alterna); a primeira que alterna de verdade é a 745. O 744 entra porque é o último
pixel do **separador do cabeçalho**, que vale 77 ali contra 68 da moldura interna em 743. Os
dois números descrevem a mesma borda; quem responde "onde a tabela começa" é a linha do
cabeçalho, e é por ela que a borda esquerda é derivada.

**Sobre as duas âncoras derivadas:** os deslocamentos `+494,−10` e `+494,+665` de
`ANCORAS_SUGERIDAS` foram medidos com o painel no meio da janela. Em `frame_000012` ele está
encostado na direita — a moldura termina em x=1711 num frame de 1720 — e a caixa de 60x60 do
`X` cairia em 1670..1730, **dez pixels além da borda**. `ancora_deslocada` EMPURRA para dentro
(1660..1720) em vez de recusar, preservando o tamanho; medido, o `X` (1685..1710) e a seta de
rolagem ficam inteiros dentro. Recusar deixaria o usuário sem sugestão justamente no frame de
calibração.

### O passo dos glifos: segmentação automática, e o usuário como revisor

**A segmentação automática da coluna de preço funcionou — não foi preciso degradar para "propor
um retângulo".** Medido nos dois frames:

| frame | linhas propostas | contagem de glifos por linha | preços na tela |
|---|---|---|---|
| `frame_000012` (calibragem) | **10 de 10** | 5,5,5,5,5,5,5,5,5,5 | 59,00 … 67,95 |
| `frame_000010` (página cheia) | **6 de 6 com preço** | 6,4,5,4,5,4 | 100,00 / 3,00 / 18,90 / 7,50 / 18,00 / 2,45 |

As quatro linhas de `frame_000010` cobertas pela tooltip caem fora **sozinhas**, sem regra
especial — não têm coluna de preço legível, então não votam. As contagens batem caractere a
caractere com o que está na tela, incluindo o `100,00` de 6 glifos, e reproduzem a segmentação
6,4,5,4,5,4 já registrada neste SUMMARY na seção da Task 1.

**Como a coluna de preço é encontrada, e por que é robusto:** pela mesma diferença de brilho que
a Task 2 mediu e que quase virou armadilha. `mascara_de_texto` (V>180) vê o número e **não** vê
o `XM Coin` ao lado (V máximo 173); `mascara_do_sufixo` (V>120) menos aquela isola a palavra
apagada. Um grupo de texto claro com uma mancha apagada limpa à direita **é** um preço com moeda.
Medido em `frame_000012`: a cauda apagada à direita do preço tem **44 colunas**, a que segue o
ícone da linha tem **9** (ela esbarra no nome dourado do item), e as colunas de nome, incremento
e carrinho dão 0, 1 e 1. Exatamente um grupo por linha qualifica.

**O usuário virou revisor:** cada retângulo abre pré-desenhado (ENTER aceita) e, quando a
ferramenta consegue ler o número pelos glifos que o próprio usuário já certificou, ela propõe a
leitura e o ENTER confirma. **O que ele digitar sempre vence**, e a conferência de contagem
continua valendo por cima da proposta (`test_a_conferencia_de_contagem_vale_TAMBEM_sobre_a_proposta`).
A certificação de que o recorte rotulado `8` é mesmo um `8` continua sendo do olho humano — é a
razão de o portão existir.

### Três medições que derrubaram a primeira implementação

Registradas porque a primeira versão de cada uma parecia certa e estava errada:

**1. O piso de 0.95 para propor a leitura matava a feature.** Eu supus que o mesmo dígito no
mesmo frame casaria 1.000 por ser o mesmo desenho. Ele não casa: o **fundo da linha alterna
entre 48 e 66** e a máscara de brilho recorta o antialias um pouco diferente sobre cada fundo.
Medido nas 10 linhas de `frame_000012`, comparando cada glifo com o molde da linha anterior:
pior acerto **0.837**, acerto típico 0.886–1.000, melhor erro **0.717** (`5` contra `6`). Com
0.95 a ferramenta não propunha nada. Passou a **piso 0.80 + margem 0.12 sobre o segundo
colocado**, copiando o par já medido de `identidade.LIMIAR_DE_CASAMENTO`/`MARGEM_MINIMA_SOBRE_O_SEGUNDO`.
Resultado sobre os dois frames: **5 propostas, 5 corretas, 0 erradas**.

**2. Votar no par `(inicio, fim)` da coluna dividia os votos.** Funcionou em `frame_000012`,
onde os dez preços têm 5 glifos e a mesma largura, e quebrou em `frame_000010`, onde `100,00`,
`18,90` e `3,00` convivem na mesma coluna **alinhada à direita**: cada largura virava um
candidato e os votos se partiam 3-2-1. Medido: **3 das 6 linhas** eram propostas, e as três
perdidas eram justamente as mais longas — as que trazem os dígitos que faltam ao conjunto.
Votando só na **borda direita**, voltam as 6, cada uma com o retângulo justo do seu número.

**3. Detectar as bordas de banda por derivada escolhia o lado errado.** A versão inicial marcava
borda onde o perfil dava um degrau e colapsava bordas vizinhas ficando com a de maior degrau.
Isso passava no frame real **por coincidência de magnitudes** (o separador do cabeçalho entra
com 23 níveis e sai com 52, então a borda gravada era a de baixo, a correta). Num painel com
mais contraste acima do separador — 70 contra 52 — a borda gravada vira a de cima, a cadeia se
desalinha em 1 px e a grade sai com **nove** linhas começando na linha do separador. Trocado por
detecção de **trechos de nível constante**: uma banda é um trecho longo, a linha de transição e
o separador são trechos de 1 linha e caem fora sozinhos. O mesmo bug, numa forma diferente, já
tinha comido a última banda: o colapso de 5 px alcançava a borda do rodapé em 1073 e a grade
saía com 9 linhas.

### O que este desvio deliberadamente NÃO faz

- **Não recusa.** `_avisar_divergencia_da_grade` diz alto quando o desenho do usuário se afasta
  do medido em mais de meia linha, com os dois números na tela — e segue em frente. Recusar
  deixaria como único caminho de correção editar o `calibration.json` à mão, que é literalmente
  o que o critério 3 do ROADMAP proíbe. O usuário é a autoridade; o trabalho da ferramenta é
  tornar a resposta certa fácil e a errada visível.
- **Não remove nenhum caminho.** Sem calibração anterior (primeira rodada da vida), sem casamento
  de âncora, ou quando a medição não fecha, cada janela abre vazia e o arrasto é o de sempre.
- **Não toca na party.** `sugestao` tem padrão `None`; `calibrar_selecionando` não passa nada.
- **Não inventa quando não sabe.** `medir_a_grade`, `localizar_o_titulo` e
  `sugerir_a_coluna_de_preco` devolvem `None`/vazio em vez de palpite. Uma sugestão errada é
  pior que nenhuma: o usuário aperta ENTER nela.

### O detalhe do `cv2.selectROI` que forçou o desenho da interação

`cv2.selectROI` devolve `(0,0,0,0)` **tanto no ESC quanto no ENTER-sem-arrasto**, e não expõe
qual tecla encerrou. Com uma sugestão na tela essas duas intenções são opostas — "aceitar" e
"cancelar" — com a mesma assinatura. Adivinhar entre elas seria exatamente o "aceitar calado"
que este desvio veio consertar. Por isso a pergunta acontece **antes** do `selectROI`, num laço
de teclado próprio (`_decidir_sobre_a_sugestao`): ENTER aceita, ESC cancela, qualquer outra tecla
devolve o arrasto. **Sem sugestão, `(0,0,0,0)` continua significando cancelar.**

O laço vive fora de `_selecionar_regiao` também por um tripwire herdado:
`test_o_selecionar_regiao_usa_o_dreno_por_tempo` proíbe a palavra `break` naquele fonte, porque
foi um laço com `break` que esvaziava a fila de teclas cedo demais e deixava o ENTER vazar para
a seleção seguinte.

### Verificação deste desvio

- `python -m pytest tests/ -q` → **1689 passed, 13 skipped**, contra a linha de base de
  **1638 passed, 8 skipped** neste worktree. **Zero regressões**; +51 testes novos e +5 skips
  (os testes contra os frames reais, que rodam no checkout principal).
- Os cinco testes contra os frames REAIS foram executados à mão apontando para
  `recordings/` do checkout principal: **os cinco passaram**, afirmando 0.9999 em (1176,362),
  topo 618 / passo 45 / 10 linhas / esquerda 744, as contagens 5×10 e 6,4,5,4,5,4, e que o
  retângulo proposto do `XM Coin` não contém nenhum pixel de dígito claro.
- **Fluxo completo end-to-end** sobre o frame real, com o seletor dublado como "o usuário
  apertou ENTER em tudo": os 5 retângulos + 10 números + a palavra foram todos oferecidos com
  sugestão (nenhum caiu no caminho sem proposta), a grade gravada saiu
  `10 linhas de 45 px, layout 'adena'` **sem o aviso de divergência**, e 11 glifos foram
  gravados com limiar 0.8275. O bloco final anunciou `FALTAM 2 GLIFO(S): 8, Adena` — exatamente
  o previsto pelo plano para aquele frame.
- `ruff check` limpo nos quatro arquivos tocados.
- Os dois tripwires de escrita de imagem seguem verdes; `grep -c imwrite` →
  `calibrar_mercado.py: 0`, `mercado_geometria.py: 0`.
- `git diff --stat` **não** toca `rastreador.py`, `visao.py` nem `sessao.py`. Nenhuma dependência
  nova — FIRE-01 intacto. `VERSAO_DO_ESQUEMA` segue 2; nenhuma chave nova de calibração foi
  criada por este desvio. `calibration.json` não foi tocado.

### O que ainda exige a mão do usuário — dito sem rodeio

Um agente não tem mouse, e nenhuma medição substitui isso. O que continua **não verificado**:

1. **Que a janela pré-desenhada aparece e o ENTER a aceita na máquina do usuário.** A geometria
   está provada (`getWindowImageRect` bate com a imagem, que foi como o CR-01 foi pego) e a
   lógica de tecla está testada com o HighGUI dublado — mas "testado com dublê" não é a mesma
   afirmação que "um humano apertou ENTER e funcionou".
2. **Que o retângulo verde está no lugar certo aos olhos dele.** Os números reproduzem o medido;
   só o olho confirma que aquilo é a área da lista que ele quer.
3. **Que o crop rotulado `8` é mesmo um `8`.** Isso é o portão da Task 3 e continua de pé.

**O portão da Task 3 do plano segue aberto** — este desvio o desbloqueia, não o cumpre.

## OS ARQUIVOS RESGATADOS

| arquivo | forma | bytes | conteúdo |
|---|---|---|---|
| `tests/fixtures/mercado/glifos_precos_f010.png` | (240, 45, 3) | 5.354 | `100,00`, `3,00`, `18,90`, `7,50`, `18,00`, `2,45` |
| `tests/fixtures/mercado/glifos_unitario_f010.png` | (30, 40, 3) | 769 | `6,00` |

Somam 5.354 + 769 = **6.123 bytes**, abaixo do teto de 8 KB. Conferidos com o olho
antes do commit: **só dígitos** — nenhum nome de personagem, nenhuma linha de chat, nenhum
nome de item. Recortados por script descartável, fora do repositório: os dois módulos de
calibração têm tripwire estrutural contando escrita de imagem no fonte, e ambos seguem em
**zero** ocorrências.

## GLIFOS GRAVADOS / FALTANTES

Nenhum glifo foi gravado em `calibration.json` por esta execução — **isso é o portão da
Task 3**, e gravar sem a mão humana seria simular o critério que o plano existe para
cumprir. Os onze glifos estão provados contra os pixels reais nas fixtures; o que falta é o
usuário produzi-los na máquina dele, mais as duas palavras de sufixo.

## VERIFICAÇÃO

- `python -m pytest tests/ -q` → **1638 passed, 8 skipped**, contra a linha de base de
  **1552 passed, 8 skipped** neste worktree (1558/2 no checkout principal — mesmo total de
  1560; os 6 skips a mais são os testes que dependem de `recordings/`, ausente no worktree).
  **Zero regressões.** O flake conhecido do `tests/test_agenda.py` apareceu uma vez e passou
  na re-execução, como previsto.
- `tests/test_mercado_glifos.py` → 47 passed. `tests/test_calibrar_mercado.py` → 110 passed.
- Os dois tripwires de escrita de imagem seguem verdes; `grep -c imwrite
  l2scanner/calibrar_mercado.py` → **0**.
- `git diff --stat` **não** toca `rastreador.py`, `visao.py` nem `sessao.py`;
  `grep -ic mercado l2scanner/rastreador.py` → **0**.
- `VERSAO_DO_ESQUEMA = 2`; `calibration.json` segue gitignored e não foi tocado.
- Nenhuma dependência nova — FIRE-01 intacto.

## Deviations from Plan

**1. [Rule 1 - Bug] Palavras de sufixo abaixo do piso de brilho dos dígitos**
- **Encontrado durante:** Task 2, ao desenhar o caminho de marcação das palavras
- **Problema:** o plano assumia a máscara dos dígitos para as palavras; medido, `XM Coin`
  tem V máximo 173 e **zero** pixels acima do piso de 180. O molde sairia vazio.
- **Correção:** `VALOR_MINIMO_DO_SUFIXO = 120` + `recortar_sufixo`, com o platô medido; e o
  guard de altura do conjunto escopado aos glifos de um caractere, para não recusar a
  calibração correta.
- **Arquivos:** `l2scanner/calibrar_mercado.py`, `l2scanner/mercado_visao.py`,
  `tests/test_mercado_glifos.py`
- **Commit:** `8608229`

**2. [Rule 1 - Bug] `ler=input` como valor padrão amarrava o `input` do import**
- **Encontrado durante:** Task 2. Resolvido em tempo de chamada. Commit `59fc6e8`.

**3. [Rule 3 - Bloqueio] Testes existentes do fluxo completo passaram a ler do stdin**
- O fluxo completo ganhou um passo (o corte de glifos), então quatro cenários existentes
  precisaram responder "terminar". Comportamento anterior preservado. Commit `59fc6e8`.

**4. [Rule 2 - Funcionalidade crítica ausente] A ferramenta descrevia em prosa e aceitava calada**
- **Encontrado durante:** a Task 3 (o portão humano), na primeira tentativa real do usuário
- **Problema:** as cinco instruções em prosa produziram cinco interpretações; uma delas gravou
  uma grade com 11 linhas. Quatro dos cinco retângulos não têm guarda nenhuma contra isso, e a
  ferramenta já sabia onde tudo estava (âncora a 0.9999, grade derivável do perfil vertical).
  Aceitar em silêncio um retângulo que se pode medir é o modo de falha que este projeto inteiro
  existe para eliminar — e era a ferramenta cometendo-o, não o usuário.
- **Correção:** `l2scanner/mercado_geometria.py` novo (medição pura), `sugestao` opcional em
  `_selecionar_regiao`, as cinco regiões + os números de preço + a palavra de moeda propostos, a
  leitura do preço proposta pelos glifos já certificados, e um aviso de divergência que informa
  sem nunca recusar. Detalhes, números e as três medições que derrubaram a primeira
  implementação: seção **"O DESVIO GRANDE"** acima.
- **Arquivos:** `l2scanner/mercado_geometria.py`, `l2scanner/calibrar.py`,
  `l2scanner/calibrar_mercado.py`, `calibrar-mercado.bat`,
  `tests/test_sugestao_de_calibracao.py`, `tests/test_calibrar_mercado.py`
- **Commits:** `ea699bb`, `a52f04b`, `0defa09`, `f5c3b1d`

**5. [Rule 1 - Bug, no meu próprio trabalho] A derivada escolhia o lado errado da borda**
- **Encontrado durante:** o desvio 4, ao construir o painel sintético para o teste
- **Problema:** a detecção de bordas por degrau + colapso "fica com o maior" acertava no frame
  real por coincidência de magnitudes. Com mais contraste acima do separador, a grade saía com
  9 linhas começando na linha do cabeçalho — o mesmo erro que o desvio existe para impedir.
- **Correção:** detecção por trechos de nível constante, mais desempate de cadeia pelo erro
  total em vez da ordem de iteração. Commits `ea699bb` (o módulo) e `f5c3b1d` (os testes das
  três regressões).

## Known Stubs

Nenhum. Todo caminho novo tem implementação real e teste.

## Threat Flags

Nenhuma superfície nova além da já registrada no `<threat_model>` do plano. Zero
dependências novas; nenhuma escrita de imagem própria; `calibration.json` segue como a única
saída, gravada pelo caminho atômico já existente.

## Self-Check: PASSED

Arquivos afirmados, conferidos no disco: `tests/test_mercado_glifos.py` (27.679 B),
`tests/fixtures/mercado/glifos_precos_f010.png` (5.354 B),
`tests/fixtures/mercado/glifos_unitario_f010.png` (769 B), `calibrar-mercado.bat` (4.112 B),
`l2scanner/calibrar_mercado.py`, `l2scanner/mercado_visao.py`, `l2scanner/calibracao.py`.

Commits afirmados, conferidos no `git log`: `d3dbcc2`, `f33883c`, `8608229`, `710eca6`,
`59fc6e8` — todos presentes, na ordem citada.

**Self-check do desvio de 2026-08-29:** arquivos conferidos no disco —
`l2scanner/mercado_geometria.py`, `tests/test_sugestao_de_calibracao.py`,
`l2scanner/calibrar.py`, `l2scanner/calibrar_mercado.py`, `calibrar-mercado.bat`. Commits
conferidos no `git log`: `ea699bb`, `a52f04b`, `0defa09`, `f5c3b1d` — todos presentes, na
ordem citada.

## Known Stubs (atualizado 2026-08-29)

Nenhum stub de código. O que segue **não verificado por máquina**, e está dito assim de
propósito, é o que exige mouse humano: que a janela pré-desenhada apareça e o ENTER a aceite, e
que o retângulo verde caia onde o usuário espera. A geometria e a lógica de tecla estão
testadas (com HighGUI dublado, e com `getWindowImageRect` no caminho real); o gesto humano não
está. É o portão da Task 3, que segue aberto.
