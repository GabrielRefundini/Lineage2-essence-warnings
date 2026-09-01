---
slug: redesenho-do-sinal-de-oclusao
workstream: mercado
created: 2026-09-01
status: awaiting_human_verify
severity: alta
hypothesis: >
  A premissa do sinal esta errada, nao a sua posicao. "Existe uma faixa
  HORIZONTAL vazia a direita do nome" e falso para os nomes reais do mercado do
  usuario. Mover a faixa so adia o defeito ate o proximo item de nome mais longo.
next_action: >
  O usuario roda `.venv/Scripts/python.exe tools/medir_oclusao.py --gravar`
  para persistir a banda no `calibration.json`, e confere em campo na aba
  Enhancement > Scrolls que as dez linhas de nome longo passam a ser lidas.
---

# O sinal de oclusao precisa parar de depender de espaco vazio horizontal

## O que ja falhou, duas vezes, medido

**Sonda original `207..417`** — sobrepunha 159 px da coluna do nome (49% dela).
Recusava as 4 linhas de `Protecting Scroll: Enchant C-grade Armor` (40 chars).
Consertado em 31/08 movendo para `246..396`.

**Sonda atual `246..396`** — RECUSA AS DEZ LINHAS de
`Protecting Scroll: Enchant C-grade Weapon` (41 chars).

    gravacao: recordings/20260901-000043-nome-longo-weapon (5 frames, janela completa)
    ponta da tinta: 255 em TODAS as 10 linhas, em TODOS os 5 frames
    sonda dx0:      246
    MARGEM:         -9 px

## A progressao que prova a premissa errada

    nome                                 chars   ponta da tinta
    Protecting Scroll: Enchant C-grade Armor    40   247
    Protecting Scroll: Enchant C-grade Weapon   41   255

Um caractere empurrou 8 px. A sonda em 246 ja estava **1 px atras** do `Armor` —
o conserto de 31/08 nasceu com margem NEGATIVA e passou nos testes porque o
gabarito nao continha o pior caso. **E o mesmo defeito do GABARITO_LIMPAS,
repetido seis horas depois por quem o consertou.**

Nomes mais longos existem (`...Enchant B-grade Weapon`). Mover de novo adia.

## O que a investigacao anterior ja mediu, e que sustenta o redesenho

- **Nao existe faixa horizontal limpa de 210 px no pior caso.** Maximo 172 px
  contra frames verificados; **56 a 91 px contra o censo de 3994 linhas**. A
  sonda precisa de 150.
- **O corredor alternativo `433..514` esta DESQUALIFICADO**: uma linha coberta
  le dispersao 0,0000 dentro dele — seria CEGO para tooltip.
- **Em todos os candidatos quem aperta e o MARCADOR DE ALVO** (0,077 / 0,022 /
  0,021), nunca a tooltip (0,32 a 0,62).

## Direcoes a MEDIR (nenhuma escolhida)

1. **Margens VERTICAIS da linha** — a linha tem 45 px de altura e o glifo nao
   ocupa tudo. Espaco acima/abaixo do texto existe por construcao, e nao encolhe
   quando o nome cresce.
2. **A moldura entre linhas** — separador da grade, desenho FIXO da UI, com
   tamanho independente do nome.

Qualquer uma precisa ser medida contra o gabarito COM os frames de nome longo,
e precisa mostrar separacao entre linha limpa e linha coberta comparavel ou
melhor que a atual.

## Restricoes invioláveis

- **NAO afrouxar o sinal.** Ele e a guarda contra tooltip SEMITRANSPARENTE — ela
  nao apaga o numero, ela o MISTURA, e numero misturado produz glifo plausivel
  com valor errado e confianca alta. E o modo de falha do incidente 27x.
- **NAO baixar** `mercado_minimo_de_linhas_comparadas` (7).
- Limiar mora no `calibration.json`, NUNCA no fonte.
- **O gabarito da ferramenta TEM de incluir os frames de nome longo**, e
  `conferir_o_gabarito_limpo` deve reprovar varredura sem eles.
- **NAO escrever** em `calibration.json` sem dizer ao usuario o comando; **NAO
  escrever** em `.mercado/`.
- **NAO tocar** `rastreador.py` nem o gate de brilho da barra propria em
  `visao.py`. Nao tocar `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`,
  `test_bosses.py` — outro agente trabalha neles nesta arvore.
- `recordings/` e somente-leitura. **NUNCA usar glob amplo nela** — `pre-voo`
  sozinha tem 1502 PNGs e varreduras assim ja mataram dois agentes por rate
  limit. As gravacoes uteis aqui sao nomeadas: as 8 do censo mais
  `20260901-000043-nome-longo-weapon`.
- Nenhuma dependencia nova (FIRE-01). Nenhum `--amend`.

## Se a conclusao for que nenhum sinal serve

E um achado legitimo. Reporte em vez de forcar — e nesse caso o paliativo
declarado e voltar a sonda para `207..417`, que ao menos le os nomes curtos.


# MEDICAO DE 2026-09-01 — as duas direcoes, contra o gabarito COM nome longo

Gabarito desta medicao: as 120 linhas LIMPAS (as 70 do gabarito do censo mais
as 50 dos 5 frames de `20260901-000043-nome-longo-weapon`), contra as 10
COBERTAS conhecidas (8 sob tooltip, 2 sob marcacao de alvo). A grandeza e a
mesma de sempre: `mercado_geometria.nivel_de_fundo_da_linha`.

## Confirmacao barata da evidencia herdada

    linha_limpa_nome_longo_par_f060 (`...C-grade Armor`,  40 ch)  ponta x=246
    linha_limpa_nome_longo_weapon_par_f000 (`...Weapon`,  41 ch)  ponta x=255

A sonda em vigor comeca em x=246. Margem -9 px. Confirmado, nao redescoberto.

## A sonda EM VIGOR, medida contra o gabarito ampliado

    populacao                        n     min      mediana    MAX
    LIMPAS do censo                 70   0,0000    0,0000    0,0007
    LIMPAS de nome longo (weapon)   50   0,0114    0,0116    0,0119
    COBERTA por tooltip              8   0,3200    0,4037    0,5945
    COBERTA por marcacao de alvo     2   0,0208    0,0210    0,0211

    pior LIMPA 0,0119   melhor COBERTA 0,0208   folga 1,8x
    contra o limiar em vigor (0,003607): 50 das 120 linhas LIMPAS RECUSADAS
    sob deriva de +-2 px na origem da linha: folga 0,3x — as populacoes INVERTEM

A folga de 30,8x que justificou o conserto de 31/08 era um numero sobre uma
populacao que nunca tinha visto o pior caso. Contra o gabarito ampliado ela e
1,8x, e sob deriva ela e menor que 1.

## DIRECAO 2 — a moldura entre linhas: REFUTADA POR MEDICAO

A premissa ("desenho FIXO da UI, tamanho independente do nome") e VERDADEIRA. A
grandeza e que nao a enxerga. O separador entre linhas e o DEGRAU da listra
alternada (48 -> 66): sobre um degrau, a fracao de pixels afastada da moda e
~0,5 POR CONSTRUCAO, exatamente a magnitude que uma tooltip produz.

    banda                    pior LIMPA   tooltip    alvo     folga
    x[42,489) dy[43,45)        0,5000     0,4944    0,5000     1,0x   NAO SEPARA
    x[42,489) dy[42,45)        0,6667     0,4944    0,5220     0,7x   NAO SEPARA
    x[42,489) dy[41,45)        0,5000     0,4944    0,5000     1,0x   NAO SEPARA
    x[42,489) dy[40,45)        0,4000     0,4944    0,4000     1,0x   NAO SEPARA
    x[42,489) dy[38,45)        0,2867     0,4944    0,3004     1,0x   folga 1,0x

Uma linha LIMPA le 0,50 na moldura. Nao ha limiar que separe. Direcao morta, e
a causa e estrutural: a sonda mede UNIFORMIDADE, e um separador e precisamente
a nao-uniformidade que o desenho da UI poe ali de proposito.

## DIRECAO 1 — as margens verticais da linha

Onde a tinta mora dentro dos 45 px da linha, nas 120 linhas LIMPAS:

    faixa de x           tinta em dy
    icone   [  0, 42)      [ 6, 37]
    nome    [ 42,366)      [15, 26]     <- o nome so ocupa 12 dos 45 px
    qtd     [366,489)      [19, 26]
    total   [489,698)      [ 0, 44]     <- EXCLUIDA: arte de dy 0 a 44
    unit    [698,872)      [ 0, 44]     <- EXCLUIDA
    cauda   [872,944)      [14, 22]

A janela x[42,489) — que e EXATAMENTE a `janela_de_busca` ja derivada das
colunas calibradas — tem tinta so em dy[15,26]. Sobram 15 px de margem em cima
e 16 px embaixo, e NENHUM DOS DOIS ENCOLHE QUANDO O NOME CRESCE.

### 1b — margem de BAIXO: separa, mas fraca e fragil

    dy[28,36)  pior LIMPA 0,0045  alvo 0,0089  folga  2,0x   sob deriva 0,5x
    dy[29,39)  pior LIMPA 0,0045  alvo 0,0474  folga 10,6x   sob deriva 1,0x
    dy[30,42)  pior LIMPA 0,0037  alvo 0,0337  folga  9,1x   sob deriva 0,3x

### 1a — margem de CIMA: VENCE

    dy[ 0, 8)  pior LIMPA 0,0020  alvo 0,2206  folga 112,7x  sob deriva  0,9x
    dy[ 1, 9)  pior LIMPA 0,0025  alvo 0,2357  folga  93,7x  sob deriva  1,7x
    dy[ 2,10)  pior LIMPA 0,0031  alvo 0,2497  folga  81,2x  sob deriva 52,6x  <-
    dy[ 2,12)  pior LIMPA 0,0034  alvo 0,2602  folga  77,5x  sob deriva 48,6x
    dy[ 3,12)  pior LIMPA 0,0037  alvo 0,2560  folga  68,7x  sob deriva 39,7x

## A ESCOLHA, e por que a DERIVA entra no criterio

`dy[0,8)` tem a melhor folga ESTATICA (112,7x) e desaba para 0,9x quando a
origem da linha anda 2 px: a -2 px ela come a moldura da linha de cima. E o
mesmo formato de defeito de 31/08 — uma escolha equilibrada no fio da navalha,
que passa porque a medicao nao exercitou o caso vizinho. Por isso o criterio de
escolha passa a ser a folga NO PIOR CASO sobre deriva de +-2 px, e nao a folga
no ponto calibrado. A deriva de 2 px nao e hipotese: `altura_da_linha` e um
inteiro (45) para um passo que pode ser fracionario, e o erro acumula ate a
decima linha; e a origem vem de casamento de molde em pixel inteiro, com o pior
positivo de campo em 0,41 (tooltip sobre a faixa de titulo).

VENCEDORA: **x[42,489) dy[2,10)**, folga 81,2x estatica e 52,6x sob deriva.

    populacao                        n     min      mediana    MAX
    LIMPAS (120, com nome longo)   120   0,0000    0,0021    0,0031
    COBERTA por tooltip              8   0,4944    0,5129    0,5171
    COBERTA por marcacao de alvo     2   0,2497    0,2876    0,3255

    contra o limiar EM VIGOR (0,003607): 0 das 120 linhas LIMPAS recusadas

## Por que o MARCADOR DE ALVO deixa de ser o gargalo, e e mecanismo, nao sorte

Em toda sonda HORIZONTAL o aperto vinha do marcador de alvo (0,077 / 0,022 /
0,021). Aqui ele le 0,2497 — doze vezes melhor. A causa e geometrica: o marcador
e uma MOLDURA em volta da linha, e a borda horizontal dela atravessa a largura
inteira no ALTO da linha. Uma sonda de 150x41 px cruza essa borda em ~2 de 41
linhas de pixel (~5%); a banda de 447x8 px a cruza em 2 de 8 (25%). A aritmetica
fecha com o medido: 0,2497 ~ 2/8.

## A propriedade que o redesenho compra, e que nenhuma mudanca de posicao compra

A banda usa a JANELA INTEIRA em x — os 447 px de `janela_de_busca` — em vez de
150 px espremidos depois da ponta do nome. Nao ha `dx0` a escolher, entao NAO HA
proximo item mais comprido que empurre a sonda para fora. `...B-grade Weapon`,
`...S-grade Armor`, um nome de 60 caracteres: todos escrevem em dy[15,26], e a
banda esta em dy[2,10). O defeito nao e adiado, e retirado de circulacao.

De quebra, a divida escrita em `LARGURA_DA_SONDA` — "sonda estreita cabe dentro
de um buraco uniforme da arte da tooltip" — ANDA PARA TRAS: a sonda vai de 150
para 447 px de largura, tres vezes mais dificil de esconder num vao do desenho.


# O QUE FOI FEITO, 2026-09-01

## A escolha, e quem a fez

A varredura escolheu, contra as 9 gravacoes (as 8 do censo mais os 5 frames de
nome longo), 190 bandas candidatas:

    BANDA: x em [42, 489) e dy em [3, 11), folga 0

    pior linha LIMPA (120 linhas)          0,0036
    coberta por marcacao de alvo (2)       0,2497   <- o caso apertado
    coberta por tooltip (8)                0,4950
    folga                                  68,7x na origem, 49,3x sob deriva
    folga ate o texto                      4 px
    folga ate a moldura da linha anterior  3 px

    limiar proposto                        0,030130
    piso de linhas comparadas              7  (INALTERADO, e re-derivado)
    custo do corte no censo                758 de 4.819 linhas (15,7%)
    linhas de nome longo recusadas         0 de 50   (eram 50 de 50)

Eu NAO escolhi a banda. A varredura escolheu, e a diferenca de um pixel entre
`dy[2,10)` (o que a minha medicao exploratoria achou) e `dy[3,11)` (o que a
ferramenta gravou) tem causa medida: a exploracao adquiria o painel do zero em
cada frame e a ferramenta o SEGUE de frame em frame, como a producao faz. As
duas origens diferem de ~1 px. Isso e a propria deriva que o novo criterio
existe para absorver, e as duas bandas separam com folga de duas ordens de
grandeza. O numero que vale e o da ferramenta.

## "O limiar subiu de 0,003607 para 0,030130" NAO e afrouxamento

Este era o risco obvio da mudanca e ele foi MEDIDO, nao argumentado. A secao
`A SENSIBILIDADE DO CORTE` da ferramenta varre o limiar de 0,25x a 4x:

    fator   limiar      recusadas de 4.819
    0,25x   0,007533    781   (16,2%)
    0,50x   0,015065    773   (16,0%)
    1,00x   0,030130    758   (15,7%)
    2,00x   0,060260    745   (15,5%)
    4,00x   0,120520    704   (14,6%)

Mexer o limiar por um fator DEZESSEIS move a recusa em 1,6 ponto percentual. O
corte pousa num vale vazio: nao ha massa de linhas de campo entre 0,0036 e
0,2497 nesta grandeza. O limiar sobe porque a populacao COBERTA subiu (0,0208
-> 0,2497 no caso apertado), e nao porque a peneira passou a tolerar sujeira.
A peneira aperta: a folga vai de 1,8x para 68,7x contra o MESMO gabarito.

## As guardas, que agora sao executadas e nao prometidas

- `PIOR_NOME_CONHECIDO_EM_CARACTERES` 40 -> 41, e o gabarito limpo carrega os 5
  frames que declaram esse nome.
- A conferencia (3) do `conferir_o_gabarito_limpo` era de ALCANCE ("a tinta
  chega ao dx0 da sonda?") e virou de FOLGA VERTICAL. A troca era obrigatoria:
  com a banda usando a janela inteira em x, a pergunta antiga responde "sim"
  para qualquer nome — virou vacua, e guarda vacua e pior que nenhuma porque
  parece verde.
- A escolha passa a ranquear pela folga NO PIOR CASO sob deriva de +-2 px.
  Este e o conserto do FORMATO do defeito: as duas escolhas anteriores foram
  feitas pela folga no ponto calibrado, e as duas nasceram equilibradas numa
  margem que o campo desfez. MEDIDO, `dy[0,8)` tem a MELHOR folga estatica de
  todas (112,7x) e desaba para 0,9x ao andar 2 px.
- `tests/test_medir_oclusao.py` e novo: ate hoje NENHUMA guarda desta
  ferramenta tinha teste. Sao 18, e cada uma executa uma guarda contra dados
  montados onde a resposta e conhecida por construcao.

## DECISOES QUE EU TOMEI SOZINHO, E POR QUE

O usuario autorizou execucao autonoma e nao havia a quem perguntar. Registro em
prosa o que decidi, para que ele possa desfazer qualquer uma na volta.

**(1) Escolhi a margem vertical DE CIMA, e nao a de baixo.** As duas foram
medidas. A de baixo separa (melhor caso 10,6x) mas e fragil a deriva (0,3x a
2,0x) porque a borda inferior da marcacao de alvo e as descidas dos glifos da
coluna de quantidade moram la. A de cima da 68,7x e segura 49,3x. Nao foi
gosto: as duas tabelas estao acima.

**(2) NAO mexi em `GRAVACOES_DO_CENSO`.** Minha primeira versao empurrou a
gravacao de nome longo para dentro do censo, e isso quebrou 8 testes de outras
tres ferramentas — inclusive um que afirma que o fixture VERSIONADO
`leituras_de_nome.json` (3.511 linhas lidas por OCR) cobre exatamente as oito
gravacoes. "Consertar" aquele teste exigiria reprocessar 3.511 linhas com o
motor de OCR, trabalho sem relacao nenhuma com a sonda de oclusao. Criei
`GRAVACOES_DA_VARREDURA = GRAVACOES_DO_CENSO + (nome-longo,)`: o censo e um
artefato historico datado, e nao "o material que as ferramentas medem".

**(3) Deixei a calibracao ANTIGA funcionando, em vez de recusa-la.** Uma sonda
sem `dy0`/`dy1` cai no comportamento de 31/08 — a linha inteira em altura. Nao
e "aceita tudo": e a geometria que erra FECHADO, recusando linha limpa. A
alternativa era `CalibracaoInvalida`, que impediria o programa de SUBIR ate o
usuario rodar a varredura. Derrubar o scanner de madrugada por causa de uma
chave nova me pareceu pior que continuar com o defeito conhecido por mais
algumas horas. `mercado_pagina` avisa UMA VEZ no log, na construcao, com o
comando a rodar. Uma sonda com `dy0` e SEM `dy1` (ou invertida), essa sim, e
recusada: nao e calibracao antiga, e calibracao quebrada.

**(4) NAO escrevi no `calibration.json` nem no `.mercado/`.** O comando esta no
relatorio, e ele e do usuario.

**(5) NAO apliquei o paliativo `207..417`.** Ele nao e mais necessario: a banda
resolve o caso que o motivou. Se o usuario discordar da banda, o paliativo
continua disponivel e nao foi consumido.

## O QUE CONTINUA SENDO DIVIDA, escrito para nao sumir

- **O gabarito COBERTO tem 10 linhas.** Oito sob tooltip, duas sob marcacao de
  alvo. O vale entre 0,0036 e 0,2497 esta vazio no material que existe, e
  material que nao existe nao foi medido. Uma cobertura de outro tipo — um
  menu de contexto, uma janela de troca — pode ler no meio. Gravar 30 segundos
  de cada uma e o proximo passo barato.
- **A banda ve a metade ESQUERDA da linha** (colunas do nome e da quantidade).
  Uma tooltip inteiramente sobre Total/Unit price continua invisivel para ela,
  e quem pega esse caso e a peneira seguinte. Isso nao mudou, e nao piorou.
  As colunas Total e Unit price NAO podem entrar na janela: MEDIDO, a arte
  delas escreve de dy 0 a dy 44 e nao deixa margem vertical nenhuma.
- **A deriva conferida e de +-2 px** e vem de dois mecanismos (altura de linha
  inteira para um passo talvez fracionario; origem por casamento de molde em
  pixel inteiro). Nao foi medida diretamente em campo — foi limitada. Se
  aparecer deriva maior, o numero sobe e a varredura roda de novo.
