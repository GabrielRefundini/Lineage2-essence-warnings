# As fixturas da leitura da renda

Todas estas imagens foram **resgatadas** de `recordings/` por
`tools/resgatar_fixturas_da_renda.py`, e nenhum teste le `recordings/`
diretamente: a pasta e gitignored e nao vem de clone limpo, entao um teste
apoiado nela ficaria verde nesta maquina e amarelo em qualquer outra.

## A gravacao de campo, e a verdade lida a olho

`recordings/20260902-004500-renda-duas-instancias/`, 2026-09-02, com as **duas
instancias vivas**. E a unica gravacao desta arvore que mostra o **nivel**, e a
unica com verdade de campo escrita (`01-MEDICOES-DE-CAMPO.md`):

| campo | Faerlina | Yazalaque |
| ----- | -------- | --------- |
| nivel | 67 | 69 |
| EXP | 8,0012% | 76,6646% |
| bonus | 592% | 612% |
| L-Coin | 13.091 | 9.790 |
| adena | 13.160.684 | 1.696.020 |

Uma fixtura sem verdade de campo prova que o codigo faz alguma coisa; uma com
verdade de campo prova que ele faz a coisa **certa**.

## A segunda rodada de campo, 8h30 depois — e o retangulo que ela derrubou

`recordings/20260902-093000-renda-segundo-cenario/`, mesmas duas instancias,
outro cenario atras da barra semitransparente.

| campo | Faerlina 00h45 | Faerlina 09h30 |
| ----- | -------------- | -------------- |
| adena | 13.160.684 | **15.134.779** |
| L-Coin | 13.091 | **14.465** |

**Ela existe aqui porque foi ela que refutou o retangulo da adena.** O
`1500,1360 200x32` tinha sido medido numa instancia cuja L-Coin era `9.790` —
curta o bastante para terminar antes de `x=1500`. Isso nao era margem, era
sorte. Com a L-Coin em `14.465` o mesmo recorte pega a cauda dela e o icone da
moeda de ouro, produzindo **corrida larga no MEIO** — a forma que a leitura por
glifo recusa.

Conferido nesta arvore, nas **quatro** fixturas de campo e nos pisos 180/185/190:
o retangulo antigo devolve um run de largura 17 no meio em **todas**. O que vale
e `1540,1358 160x34`, e a contagem do meio bate com a verdade caractere por
caractere nas quatro. `test_renda_tracer.py` prende isso.

Sem estas duas fixturas versionadas, a correcao seria prosa que ninguem
conseguiria reproduzir a partir do clone.

## As gravacoes antigas nao sao rascunho

Elas cobrem estados que a de campo nao tem:

| arquivo | o que ele prova |
| ------- | --------------- |
| `aba_para_calibrar_f000__barra_esquerda.png` | o EXP legivel no recorte **cru**, `57,9749%` (M2) |
| `aba_para_calibrar_f000__barra_direita.png` | o campo da adena em que o cru **nao** mostra a adena (M7) |
| `adena_diagnostico_f005__barra_esquerda.png` | o EXP que **some** no cru e que a mascara recupera (M4/M5) |
| `mercado_farm_com_party_f000__barra_esquerda.png` | os dois caminhos de leitura que **discordam** num digito da segunda casa (M6) |
| `segundo_cenario_*__barra_direita.png` | o cenario que derrubou o retangulo `1500,1360 200x32` (M-N/M-O) |
| `segundo_cenario_yazalaque__barra_esquerda.png` | o EXP oito horas depois, `85,2845%` — outro ponto para a taxa |

## `montagem_da_janela.png` NAO e uma captura

E uma tela preta de 1720x1392 com os recortes reais da Faerlina colados nas
posicoes de calibracao. Ela prova **geometria, posicao e o caminho de ponta a
ponta**; ela nao prova nada sobre o resto da tela do jogo, que aqui e preto.

**A regiao do nivel fica preta de proposito**, e o motivo mudou: antes ela era
preta porque nenhuma gravacao continha o nivel; hoje duas contem, e ela e preta
porque o caso de **campo vazio** tambem precisa de uma fixtura — e as de campo
entregam o caso oposto. As duas existem, e cada uma prova uma coisa.

## `calibracao_de_fixture.json` nasce SEM `renda_moldes_da_barra`

Isto e deliberado e nao esquecimento. Os moldes so existem depois da rodada
humana do cortador (plano `01-05`), e este arquivo nasceu na onda 1. O campo
**ausente** e um dos tres estados legitimos que `tests/test_renda_tracer.py` ja
prende por teste — os outros dois sao presente-e-completo e
presente-e-**incompleto**.

**Quem funde os moldes nesta fixtura e o `01-04`, na Tarefa 1 dele**, porque ele
e o consumidor e porque a onda 3 e a primeira em que os moldes existem: o
`01-05` grava `tests/fixtures/renda/moldes_da_barra.json` e para ali. Sem este
endereco escrito, o proximo leitor procura o merge no plano errado, ou dois
planos o fazem duas vezes.

## Os nomes das duas sub-chaves mentem, e a mentira esta documentada

`barra_esquerda` descreve o **EXP** e `barra_direita` descreve a **ADENA** — nao
"as metades da barra". Os nomes vem da era em que os recortes eram duas metades
de 520 px. Renomear **uma** sem a outra deixaria duas convencoes dentro da mesma
chave; quem renomear renomeia as duas, para `exp` e `adena`, num commit proprio.
