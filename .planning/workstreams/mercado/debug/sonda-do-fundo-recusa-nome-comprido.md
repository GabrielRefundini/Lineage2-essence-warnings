---
slug: sonda-do-fundo-recusa-nome-comprido
workstream: mercado
created: 2026-08-31
status: resolved
severity: alta
hypothesis: >
  A sonda de oclusao (mercado_sonda_do_fundo) esta geometricamente EM CIMA da
  metade direita da coluna do nome. Nome comprido invade a faixa, o fundo deixa
  de ser uniforme, e a linha e recusada como "ocluida" sem haver tooltip nenhuma.
next_action: nenhuma — conserto aplicado e PROVADO EM CAMPO
---

# A sonda de oclusao recusa linhas de nome comprido

## Sintoma, medido em campo

Sessao real do usuario, 2026-08-31 13:39, aba **Enhancement > Scrolls** (layout
`negociacao`, o mesmo calibrado):

    paginas lidas                    0
    paginas PERDIDAS                31
    ticks com o painel aberto       32
    frames congelados                0
    linhas descartadas             129
      oclusao                      104
      numero                        20
      discordancia-entre-escalas     5

**Nenhuma observacao gravada.** O `observacoes.csv` saiu com so o cabecalho.

## A correlacao

As linhas recusadas por `oclusao: fundo nao uniforme` foram **sempre** as de
indice 5, 7, 8 e 9 (base zero) — as **quatro** linhas de
`Protecting Scroll: Enchant C-grade Armor` (40 caracteres).

As **seis** linhas de `Scroll: Enchant D-grade Weapon` (29 caracteres) passaram
todas, em todos os 32 ticks.

Correlacao perfeita com o COMPRIMENTO DO NOME. Nao com posicao, nao com a
listra alternada, nao com a cor do icone.

## A geometria, medida do calibration.json

    borda esquerda da grade (dx)          -427
    coluna do NOME, no recorte da linha   42 .. 366   (largura 324)
    mercado_sonda_do_fundo                207 .. 417
    SOBREPOSICAO                          207 .. 366  = 159 px = 49% da coluna

A docstring de `linha_ocluida` (`l2scanner/mercado_leitura.py`, ~1207) afirma que
a sonda ve *"entre o fim dos nomes e o inicio dos numeros"*. **A geometria real
contradiz a docstring**: ela ve a metade direita da propria coluna do nome.

E nao ha vao para onde mover: a coluna de quantidade comeca em **366**,
exatamente onde a do nome termina.

## O ultimo elo

4 de 10 linhas recusadas => 6 aceitas.
`mercado_minimo_de_linhas_comparadas` = **7**.

Falta exatamente UMA linha. Por isso toda pagina e perdida.

## O leitor NAO esta errado

A linha 3 foi lida como `total=674 unitario=134 quantidade=5`; a tela mostrava
**6,74 / 1,34 / 5**. Digito por digito correto. O defeito e so a peneira.

## Restricoes do conserto

- **NAO afrouxar a sonda.** Ela e a guarda contra tooltip SEMITRANSPARENTE — a
  tooltip nao apaga o numero, ela o MISTURA, e numero misturado produz glifo
  plausivel com valor errado e confianca alta. E o modo de falha do incidente 27x.
- **NAO baixar o piso de 7** — mascararia o defeito em vez de conserta-lo.
- **A nova posicao da faixa precisa ser MEDIDA** contra frames com nome comprido,
  nunca escolhida a olho. O limiar mora no `calibration.json`, nunca no fonte.
- Se a conclusao for "nao existe faixa horizontal limpa no pior caso", isso e um
  achado legitimo e muda o desenho do sinal — reporte em vez de forcar.

## Evidencia que talvez falte

As gravacoes em `recordings/` sao da aba **Equipment**, onde os nomes sao curtos
(`Fire Spirit Evolution Stone`, `Phantom Mask Sealed`). **Pode nao existir frame
gravado com nome comprido.** Se for esse o caso, o portao e humano: o usuario
roda `--record` na aba Enhancement > Scrolls. Peca em vez de inventar frame.

## Fora de alcance

`rastreador.py` e o gate de brilho da barra propria em `visao.py` — intocaveis.
Nao escrever em `.mercado/` nem em `calibration.json`. `recordings/` e
somente-leitura e NUNCA usar glob nela (a pasta `pre-voo` sozinha tem 1502 PNGs).
Outro agente trabalha nos workstreams `tiat`/`identidade` nesta mesma arvore.


# ---------------------------------------------------------------------------
# MEDICOES DE 2026-08-31 — a hipotese esta CONFIRMADA
# ---------------------------------------------------------------------------

## 1. A evidencia que faltava EXISTE. Nao foi preciso gravar nada.

A premissa "as gravacoes sao da aba Equipment, nomes curtos" e FALSA. O censo
tem o nome exato do defeito:

    recordings/20260828-053105-mercado-aberto/frame_000060.png
    `Protecting Scroll: Enchant C-grade Armor` — 40 caracteres, nas DEZ linhas,
    SEM tooltip nenhuma (conferido a olho no frame inteiro)

    recordings/20260828-053105-mercado-aberto/frame_000052.png
    `+6 Agathion Alpha Hunter Sealed` — 31 caracteres, dez linhas, limpo

Medido sobre TODO o censo (4.690 linhas de campo, 8 gravacoes):
**28,6% das linhas ja tinham tinta de NOME passando de x=207.** A sonda nunca
foi conferida contra elas.

## 2. A CAUSA-RAIZ do erro de calibragem: o gabarito aponta para o frame errado

`tools/medir_oclusao.py:GABARITO_LIMPAS` inclui `scroll-transicao/frame_000016`
e `frame_000017` com este comentario:

    "e neles que aparecem os nomes LONGOS (`+6 Agathion Alpha Hunter Sealed`),
     e sem eles a escolha do trecho seria enganada por um recorte que so parece
     vazio porque as seis paginas conferidas tinham nome curto."

**Os dois frames foram abertos e conferidos: eles mostram
`Hardin's Soul Crystal Lv. 1` — 27 caracteres.** O nome longo esta em
`053105/frame_000052`, que NAO esta no gabarito. A guarda contra nome curto foi
escrita, foi documentada, e apontava para o lugar errado — entao a varredura
escolheu 207..417 validada so contra nome curto, exatamente a falha que o
comentario dizia estar impedindo.

## 3. A medicao que confirma a hipotese

Sonda calibrada 207..417, limiar 0,026377:

    frame_000060, nome 40ch, SEM tooltip   dispersao 0,0276-0,0278  10/10 RECUSADAS
    frame_000010, nome 28ch, limpo         dispersao 0,0000         10/10 aceitas
    frame_000052, nome 31ch, limpo         dispersao 0,0000-0,0041  aceitas

A margem e de 4,6%: 0,0276 contra um limiar de 0,0264. O nome de 40 caracteres
passa 40 px de GLIFO para dentro da sonda (a tinta do nome termina em x=247).

## 4. ONDE A FAIXA PODE MORAR — a resposta e um NUMERO, e ele e ruim

Uniao da tinta das 40 linhas VERIFICADAS limpas (4 frames), na largura inteira
da grade (944 px). Corredores 100% limpos com >= 60 px:

    x=248..419   172 px   linha coberta le no minimo 0,0152   utilizavel
    x=433..514    82 px   linha coberta le  **0,0000**        INUTILIZAVEL

O segundo corredor esta DESQUALIFICADO por medicao: uma linha coberta some
inteira dentro dele. E o mesmo modo de falha que o docstring de
`FRACAO_DA_JANELA_PARA_A_SONDA` mediu com blocos de 30 px, agora medido com 82.
Nao existe opcao "unir dois corredores".

E sobre o CENSO INTEIRO (3.994 linhas nao engolidas por overlay), o corredor
encolhe muito mais, porque entram todos os comprimentos de nome e todas as
larguras de quantidade:

    colunas NUNCA com tinta                     maior corredor =  0 px
    colunas com tinta em < 0,5% das linhas      maior corredor = 56 px (350..405)
    colunas com tinta em < 2%   das linhas      maior corredor = 91 px (323..413)

**ACHADO: nao existe faixa horizontal limpa de 210 px no pior caso.** A largura
maxima de uma faixa limpa e 172 px contra os 4 frames verificados, e cai para
56-91 px contra o censo inteiro. Manter a largura obriga a sonda a ficar em cima
do nome; sair de cima do nome obriga a estreitar. Nao ha terceira posicao.

Varredura 2-D (posicao x largura, gabarito estendido com os nomes longos):

    largura 210  melhor dx0=192  pior_limpa 0,0391  folga  2,9x
    largura 180  melhor dx0=243  pior_limpa 0,0033  folga  6,9x
    largura 150  melhor dx0=246  pior_limpa 0,0007  folga 32,0x

Contra o gabarito de frames VERIFICADOS (4 limpos, 2 cobertos):

    sonda            pior LIMPA   melhor COBERTA   folga    limiar (media geom.)
    207..417 (atual)   0,0278        0,0775         2,8x        0,046372
    243..423 (180px)   0,0033        0,0224         6,9x        0,008527
    246..396 (150px)   0,0007        0,0208        32,0x        0,003679

Em todos os tres candidatos quem aperta e a MARCACAO DE ALVO (0,077 / 0,022 /
0,021), nunca a tooltip (0,32-0,62 em todos). A tooltip tem folga de sobra; o
alvo e que e o caso dificil.

## 5. As tres saidas, e por que nenhuma e minha para escolher

(A) NAO mexer na geometria; so REMEDIR o limiar com o gabarito corrigido:
    0,026377 -> 0,046372. Conserta o defeito relatado. Mas a folga contra a
    marcacao de alvo cai de 2,9x para 1,7x — isto E afrouxar a peneira, e a
    restricao do conserto diz para nao afrouxar.

(B) Mover E estreitar: sonda 246..396 (150 px), limiar 0,026377 -> 0,003679.
    O limiar fica 7x MAIS APERTADO e a separacao sobe de 2,8x para 32,0x. Mas a
    sonda encolhe de 210 para 150 px, e sonda estreita e o que cabe dentro de um
    buraco do desenho — a restricao "NAO afrouxar a sonda" morde aqui, ainda que
    as 10 linhas cobertas conhecidas continuem recusadas com 5x de folga.

(C) Trocar o DESENHO do sinal, porque o achado do item 4 diz que faixa
    horizontal larga e limpa nao existe. Nao foi medida; e trabalho de fase.

Nenhuma das tres cabe dentro das restricoes recebidas sem que alguem gaste uma
delas de proposito. Por isso o checkpoint.

## 6. O teste RED ja existe

    tests/test_mercado_leitura.py::TestASondaDeOclusao::
        test_a_linha_de_NOME_LONGO_sem_tooltip_nenhuma_PASSA[banda_par]
        test_a_linha_de_NOME_LONGO_sem_tooltip_nenhuma_PASSA[banda_impar]

    fixturas novas (recortadas de frame_000060, as duas paridades de banda):
        tests/fixtures/mercado/linha_limpa_nome_longo_par_f060.png
        tests/fixtures/mercado/linha_limpa_nome_longo_impar_f060.png

Estado: VERMELHO nas duas paridades, `assert True is False`. Ele nao depende de
`recordings/` e vale para qualquer uma das tres saidas.


# ---------------------------------------------------------------------------
# 2026-08-31 — O CONSERTO, opcao (B): mover E estreitar
# ---------------------------------------------------------------------------

## Os dois numeros

    mercado_sonda_do_fundo               207..417 (210 px) -> 246..396 (150 px)
    mercado_limiar_de_dispersao_do_fundo 0,026377          -> 0,003607
    mercado_minimo_de_linhas_comparadas  7                 -> 7  (NAO se mexeu)

## O limiar saiu 0,003607, e nao os 0,003679 do checkpoint

A decisao trouxe 0,003679, que veio da varredura DE MAO da sessao anterior, com
4 frames limpos no gabarito. A `tools/medir_oclusao.py` — que e quem grava o
`calibration.json` — rodou agora com o gabarito CORRIGIDO, 8 frames limpos e 70
linhas limpas, escolheu sozinha o MESMO trecho `[246, 396)` e propos 0,003607:

    pior linha LIMPA        0,0007   (frame_000060, nome de 40 caracteres)
    melhor linha COBERTA    0,0200   (marcacao de alvo, o caso apertado)
    folga total             30,8x
    media geometrica        0,003607

A diferenca de 2% e da POPULACAO maior, nao do trecho, e cai dentro de um vao de
30x — nenhuma fixtura muda de veredito entre os dois numeros. Vale o da
ferramenta e nao o do checkpoint por um motivo estrutural: o usuario vai
persistir rodando `--gravar`, e um numero digitado a mao que a varredura nao
reproduz e exatamente a classe de defeito que esta sessao existe para fechar.

## O que os dois numeros custam e o que compram

    folga contra a pior linha limpa      5,5x   (0,003607 / 0,0007)
    folga contra a melhor linha coberta  5,5x   (0,0200 / 0,003607)
    linhas do censo recusadas            19,1%  (911 de 4.768)
    piso proposto de novo pela varredura 7      (teto coberto 4, p5 normal 10)

A DIVIDA, escrita para nao sumir: 150 px cabe dentro de um buraco uniforme da
arte da tooltip com mais facilidade do que 210 px cabia. O censo nao mostra
nenhum caso — a menor coberta conhecida le 0,0200 — mas o mecanismo continua de
pe. Esta escrito no bloco `LARGURA_DA_SONDA` e no docstring de `linha_ocluida`.

## O que mudou no fonte

    tools/medir_oclusao.py
      GABARITO_LIMPAS            + 053105/frame_000060 (40 ch, tinta ate x=246)
                                 + 053105/frame_000052 (31 ch, tinta ate x=208)
                                 e a prosa que apontava para o frame errado,
                                 corrigida com as quatro pontas medidas do
                                 gabarito antigo: 178, 142, 169, 169
      LARGURA_DA_SONDA           novo, 150 px, no lugar da FRACAO 0.5 (=210 px)
      PASSO_DA_VARREDURA         15 -> 12, porque 42+15k nunca cai em 246
      GABARITO_LIMPAS            passa a 4 campos: o quarto e o NOME EXIBIDO
                                 conferido a olho, ou None
      PIOR_NOME_CONHECIDO_EM_    novo, 40 — o piso que o gabarito limpo tem de
        CARACTERES               conter, e que sobe quando o campo mostrar maior
      ponta_da_tinta_do_nome     novo, mede em px ate onde o nome escreve
      conferir_o_gabarito_limpo  novo, PARA com codigo 8 — tres conferencias

    l2scanner/mercado_leitura.py
      linha_ocluida              o docstring dizia que a sonda ficava "entre o
                                 fim dos nomes e o inicio dos numeros". Era
                                 falso: nao ha tal vao, as colunas sao coladas
                                 em 366. Agora nomeia o pior caso conhecido e
                                 escreve o custo do estreitamento.

    tests/fixtures/mercado/calibracao_de_fixture.json   os dois numeros novos
    tests/test_mercado_geometria.py  SONDA_ESCOLHIDA_PELA_VARREDURA -> (246,396,2)
                                     + as duas linhas de nome longo no teste de
                                       "as linhas limpas ficam no chao"
    tests/test_mercado_leitura.py    o docstring que citava dx 207..417

## A guarda que impede a recorrencia, e a versao dela que NAO servia

A primeira tentativa foi so de ALCANCE: "a tinta mais funda do gabarito limpo
tem de chegar ao dx0 da sonda". ELA FOI REFUTADA ANTES DE ENTRAR. Rodando contra
o gabarito de 2026-08-30, a tinta mais funda nao era 178 (os frames que a prosa
citava) e sim 215, do `alvo/frame_000024`, que ninguem tinha olhado. 215 >= 207:
a guarda teria PASSADO a varredura defeituosa. Fica registrado porque o numero
178 aparece na medicao acima e induz ao erro: ele e o maior dos QUATRO frames
"comuns", nao o maior do gabarito inteiro.

`conferir_o_gabarito_limpo` faz TRES conferencias, e a que morde e a primeira:

    (1) PISO DE COMPRIMENTO   o gabarito limpo tem de declarar um nome com pelo
                              menos PIOR_NOME_CONHECIDO_EM_CARACTERES (=40) ch
    (2) DECLARACAO x PIXELS   o frame que declara o nome mais comprido tem de
                              ser tambem o de tinta mais funda entre os limpos
    (3) ALCANCE               a tinta mais funda tem de chegar a
                              min(dx0, ponta mais funda do censo)

O NOME EXIBIDO SAIU DO COMENTARIO E ENTROU NA TABELA: o quarto campo de cada
linha do `GABARITO_LIMPAS` e o nome que aquele frame mostra, e (2) o confronta
com os pixels. `None` e legitimo para o frame que ninguem conferiu a olho.

PROVA EXECUTADA, com as pontas medidas dos frames reais:

    gabarito de 2026-08-30, dx0=207            REPROVADO por (1)
      maior declarado 31 ch (`+6 Agathion Alpha Hunter Sealed`, f016)
      contra um piso de 40
    o mesmo, com o piso de caracteres desligado REPROVADO por (2)
      f016 declara 31 ch e inka ate x=169, mas alvo/f024 inka ate x=215
    gabarito de hoje, dx0=246                   PASSOU
      declarado mais comprido e o de tinta mais funda: frame_000060,
      `Protecting Scroll: Enchant C-grade Armor`, 40 ch, x=246

Nada disso e circular: comprimento declarado contra comprimento declarado, e
ponta de tinta contra ponta de tinta. Em ponto nenhum entra a dispersao ou o
limiar que a ferramenta ainda vai propor.

## A VERIFICACAO

    tests/test_mercado_leitura.py::TestASondaDeOclusao::
      test_a_linha_de_NOME_LONGO_sem_tooltip_nenhuma_PASSA[banda_par]     VERDE
      test_a_linha_de_NOME_LONGO_sem_tooltip_nenhuma_PASSA[banda_impar]   VERDE

    suite inteira   `python -m pytest tests/ --ignore=tests/test_agenda.py -q`
                    3411 passed, 2 skipped, 0 failed  (exit 0)

    a ferramenta    `python tools/medir_oclusao.py`  exit 0, e ela ESCOLHE
                    sozinha [246, 396) — o mesmo trecho da decisao

Os seis testes de sonda que ja existiam continuam verdes, e nenhuma fixtura de
pagina mudou de veredito: `f010`, `f005`, `adena_f014` e `com_linhas_vazias`
liam `..........` nos dois trechos, e `tooltip_f012` lia `XXXXXXXX..` nos dois.
O conserto move exatamente as duas linhas que o defeito recusava, e nada mais.

## O portao humano

`calibration.json` e gitignored, tem os 13 moldes de glifo a mao, e nenhum agente
escreve nele. O usuario roda, no checkout PRINCIPAL (`recordings/` nao se
materializa em worktree):

    .venv\Scripts\python.exe tools\medir_oclusao.py --gravar

Sai 0 e grava os tres numeros por load-mutate-save (os moldes atravessam
intactos). Depois: abrir a aba Enhancement > Scrolls e conferir que as linhas de
`Protecting Scroll: Enchant C-grade Armor` passam a ser lidas e que o
`observacoes.csv` deixa de sair so com o cabecalho.


## RESOLVIDO — provado em campo 2026-08-31 15:48 e 16:03

O usuario gravou a nova calibracao (`python tools\medir_oclusao.py --gravar`) e
rodou o modo na MESMA aba que falhava (Enhancement > Scrolls).

    ANTES                        DEPOIS
    paginas lidas         0      13
    paginas perdidas     31       1
    linhas descartadas  129       0
    observacoes           0      10

`calibration.json` gravado com `246..396` / `0,003607`, piso 7 REDERIVADO pela
varredura (faixa possivel (5,9), folga 3 para cada lado). Os 13 moldes cortados
a mao e as 3 ancoras passaram intactos pelo load-mutate-save; a calibracao de
party tambem.

### A leitura foi conferida CONTRA A TELA: 10 de 10 linhas exatas

Print do usuario comparado linha a linha com o `observacoes.csv`: nome, total,
quantidade e ORDEM identicos. Zero divergencia.

O unico residuo nao-zero esta explicado e CORRETO: `35,00 / 9 = 3,8888...`, o jogo
exibe `3,88` truncado, e `3500 - (388 x 9) = 8`. O residuo mede exatamente a
truncagem do jogo — e a razao de o unitario exibido nunca ter virado coluna:
reconstruir o total a partir de `3,88` devolveria `34,92`, um numero que nunca
existiu.

### Uma suspeita minha que a medicao derrubou

Eu desconfiei da ORDEM das linhas por elas nao subirem por unitario. Errado: quem
nao esta ordenado por unitario e a LISTA DO JOGO (3,00 / 3,00 / 3,25 / 10,00 /
3,88 / 2,50 ...), apesar da seta em `Unit price`. O scanner reproduziu a ordem da
tela fielmente.

### Portoes humanos da Fase 2 — os DOIS fechados nesta sessao

1. **OCR real dentro do tick** — 10/10 conferidas contra a tela, com o nome mais
   comprido do mercado (40 caracteres).
2. **Congelamento provocado** — janela minimizada, e saiu
   `CAPTURA CONGELADA: 3 janelas consecutivas bit-identicas`, recusando aceitar
   pagina. Comportamento exato do desenho.

### ANAL-01/02 provados com dado real

Console: `ABAIXO DA MEDIANA: 2,50 por unidade (derivado), contra mediana de 3,89
(derivado) com n=10`. Conferido: com n=10 (PAR), `median_low` devolve 388,89 —
que ESTA na lista — enquanto `statistics.median` devolveria 394,44, que NAO esta.
A decisao travada na Fase 4 ("um numero exibido tem de ter existido na tela")
comprovada em producao.
