---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 03
workstream: renda
subsystem: calibracao-da-renda
status: parcial
tags: [calibracao, nao-destruicao, varredura-de-piso, criterio-4, bat]
requires:
  - l2scanner.renda_leitura (_cruzar_as_escalas, decimos_de_milesimo, recortar, MOTIVO_*)
  - l2scanner.calibracao (renda_por_personagem, REGIOES_DA_RENDA, PISO_DE_BRILHO_*_DA_RENDA)
  - l2scanner.calibrar (_selecionar_regiao, _gravar_conferencia)
  - l2scanner.mercado_leitura (mascara_de_numero, numero_valido, segmentar_glifos_no_brilho)
provides:
  - l2scanner.calibrar_renda (calibrar_renda, varrer_o_piso, classificar_a_leitura, resumir_a_banda_util, escolher_o_piso, grade_de_pisos, medir_a_forma_da_adena, ordem_de_operacao)
  - calibrar-renda.bat
  - O PRIMEIRO ESCRITOR de Calibracao.renda_por_personagem
affects:
  - tests/test_calibrar_nao_apaga_identidades.py (inscricao no tripwire MODULOS_QUE_GRAVAM)
tech-stack:
  added: []
  patterns:
    - "load-mutate-save com mutacao por COPIA COM SUBSTITUICAO da chave do personagem"
    - "varredura pura separada do laco de OCR por `ler_escalas` injetavel"
    - "portao de criterio por ARVORE DE SINTAXE, nunca por texto"
key-files:
  created:
    - l2scanner/calibrar_renda.py
    - calibrar-renda.bat
    - tests/test_calibrar_renda.py
    - tests/test_calibrar_renda_bat.py
    - tests/test_calibrar_renda_nao_apaga_nada.py
    - tests/test_nenhum_numero_do_spike_no_fonte.py
    - tests/test_a_janela_movida_e_consertada_pelo_calibrador.py
  modified:
    - tests/test_calibrar_nao_apaga_identidades.py
decisions:
  - "A varredura da `barra_direita` NAO foi escrita: a peneira `_glifos_do_numero` e do `01-05`, mesma onda, e nenhuma segunda peneira foi criada para destravar"
  - "A banda util do EXP da Faerlina, medida com passo 5: 141-171, largura 7, piso do centro 156"
  - "A altura de faixa do recorte `1540,1358 160x34` e 16 EXCLUSIVA (17 inclusiva); o miolo sem os icones e 9 exclusiva (10 inclusiva), que e o `10` do M-K"
  - "ACHADO: ha uma janela de 3 px (+84..+86) em que a leitura do EXP FABRICA numero errado, e em +86 as duas escalas concordam no erro"
  - "`calibrar_renda.py` inscrito em MODULOS_QUE_GRAVAM do tripwire de identidades, com a conferencia escrita ao lado"
metrics:
  duration: ~1 sessao
  completed: 2026-09-02
actuals:
  tokens: 37581
  tasks: 2.5
  commits: 4
---

# Phase 01 Plan 03: O calibrador da renda — Summary

Um calibrador que carrega o `calibration.json` inteiro antes de tocar nele, marca as tres regioes
da renda **por personagem** com a sugestao vinda do disco, varre o piso de brilho de 5 em 5 com
**tres** veredictos em vez de dois, e prova por teste que uma rodada da Faerlina deixa a Yazalaque
byte a byte identica — mais o criterio 4 do roadmap virado portao de arvore de sintaxe.

## STATUS: PARCIAL — e a fronteira esta declarada, nao escondida

**A varredura de piso da `barra_direita` (a adena) NAO foi escrita.** Ela e classificada pelo
veredicto de **glifo**, pela peneira `renda_leitura._glifos_do_numero`, que e escrita pela Tarefa 1
do **`01-05`** — o plano da **mesma onda 2**. A precondicao declarada da Tarefa 2 deste plano foi
conferida no inicio e no meio da execucao:

    grep -c "def _glifos_do_numero" l2scanner/renda_leitura.py  ->  0

O coordenador confirmou o sequenciamento antes de a execucao chegar nesse ponto e instruiu:
executar tudo que nao depende da peneira, **parar exatamente na fronteira dela**, e nao escrever
uma peneira propria para destravar. Foi o que se fez.

**Por que nenhuma peneira propria foi escrita, alem da instrucao:** o plano proibe com razao (duas
peneiras seriam duas formas, e os moldes do `01-05` seriam cortados de um conjunto de corridas e
lidos de outro), e ha um agravante medido. As larguras deste projeto vivem em **duas convencoes**
(M-P): `larguras_de_molde` mede `fim - inicio` (**exclusiva** — digito 4/5/6, virgula 1, icones
14/15) e o `01-MEDICOES-DE-CAMPO.md` relata `fim - inicio + 1` (**inclusiva** — 5/6/7, 2, 15/16).
Uma peneira escrita as pressas contra a convencao errada **recusa o digito mais largo e aceita
icone estreito**, calada nos dois sentidos. Escrever uma sem ver a assinatura e o contrato de
retorno da verdadeira seria inventar exatamente o defeito que a fase inteira existe para nao ter.

O que ficou aberto esta na secao **"O que falta para fechar"**, no fim.

## O que foi construido

### `l2scanner/calibrar_renda.py` — o calibrador

Irmao curto de `calibrar.calibrar_tiat`, com as sete etapas na ordem que faz a nao-destruicao ser
**estrutural em vez de prometida**:

1. recusar a combinacao ilegal de argumentos, **antes de tudo**;
2. **CARREGAR** o `calibration.json` inteiro — a primeira linha util;
3. descobrir de quem e a tela, e so entao capturar pixel;
4. avisar se a janela mudou de tamanho, **antes** da primeira selecao;
5. tres selecoes, com a sugestao vinda do disco;
6. varrer o piso de cada regiao lida por OCR;
7. mutar **so** a entrada daquele personagem, e gravar.

**O nome do personagem e pre-requisito da rodada** (LEIT-07), nos dois caminhos: no `--janela` sai
do titulo por `cliente.nome_do_personagem`; no `--imagem` `--personagem` e **obrigatorio**, e a
recusa sai antes de qualquer captura. Medido (M-F), as duas instancias poem a janela de status em
`246,736` e `236,750`, e um calibrador que adivinha o personagem grava o retangulo de um por cima
do outro — a unica maneira de esta ferramenta causar exatamente o dano que ela existe para impedir.

**A sugestao vem do disco e nunca de um literal.** Da entrada do proprio personagem; na falta dela,
da de um vizinho — **sempre anunciada como tal**. As duas parecem a mesma coisa e nao sao:
*sugerir e confirmado por um humano; cair e silencioso*. A frase esta escrita ao lado do codigo
porque a proxima pessoa vai olhar os dois caminhos e achar que sao o mesmo.

**A mutacao e por copia com substituicao da chave do personagem**, nunca por reconstrucao. Um
dicionario remontado a partir do que este codigo conhece hoje apaga a sub-chave que uma versao
futura acrescentar — e apaga o personagem vizinho inteiro. E o incidente de 2026-08-30 uma camada
abaixo, com a mesma forma: um escritor montando do zero o que devia ter carregado.

`ARQUIVO_CALIBRACAO` e destino unico. `--partir-de` le de outro arquivo e por isso e legal
**somente** junto de `--so-medir`; a combinacao contraria e recusada com mensagem propria.

### A varredura de piso — funcoes puras, separadas do laco de OCR

`classificar_a_leitura` devolve **tres** veredictos (`vazio`, `nao-e-numero`, `numero`) porque os
consertos sao dois diferentes: campo vazio aponta para o retangulo, gramatica invalida aponta para
o piso. `varrer_o_piso` produz uma linha por piso com os textos crus entre delimitadores, os dois
veredictos, e **qual desfecho o cruzamento produziu** — a decisao vem de
`renda_leitura._cruzar_as_escalas` e nao de uma comparacao escrita aqui.

`resumir_a_banda_util` devolve o maior trecho **contiguo** aceito; `escolher_o_piso` devolve o
**centro** dela. A **largura** e produto de primeira classe e vai gravada junto do piso; largura 1
ou 2 sai como **aviso em voz alta** antes de gravar.

**A grade anda de 5 em 5.** O numero e a razao estao no fonte: o passo de 10 do M-E **pulou o 155**
e concluiu que a Yazalaque nao lia a adena, quando ela lia. Um passo grosso nao erra para o lado
seguro — ele produz uma conclusao errada com aparencia de medicao, e aquela conclusao entrou num
documento e do documento entrou num plano.

A fronteira que torna tudo isso testavel sem OCR e o parametro `ler_escalas` de `varrer_o_piso`.
Ele nao e um atalho de teste: e a separacao entre o laco que faz OCR e as funcoes que decidem, e e
ela que faz `tests/test_calibrar_renda.py` rodar em qualquer clone **sem um skip**.

### `calibrar-renda.bat` — dialeto B, com as tres licoes que o mercado pagou em campo

`%*` repassado; bloco de conferencia atras de um `if errorlevel 1` que encerra com `exit /b 1` e
afirma que **nada foi gravado**; e **nenhuma imagem nomeada em echo nenhum** — o `.bat` nao sabe
qual arquivo saiu, e quem nomeia o de sempre manda o usuario validar a rodada nova olhando a
imagem da anterior. Cabecalho `REM` que ensina quando rodar e diz que a calibracao e por
personagem. ASCII puro no arquivo inteiro.

### `medir_a_forma_da_adena` — a mitigacao de T-01-61

Ela **mede e nao classifica**, e e essa a fronteira que a mantem deste lado do `01-05`: imprime a
altura de faixa, a contagem de corridas e as larguras, **com a convencao declarada**, e nao
devolve veredicto nenhum (ha um teste que afirma isso). Ela existe porque **quem escolhe o
retangulo aqui escolhe a altura de faixa que a guarda do `01-05` vai usar** — sem esta medicao na
tela o usuario so descobriria o recorte contaminado duas ferramentas depois.

## As medicoes desta rodada

Todas feitas nesta arvore, contra as fixturas versionadas, e nenhuma copiada de documento.

### 1. A banda util do EXP, com o passo de 5

    calibrar-renda.bat --imagem montagem_da_janela.png --personagem Faerlina --so-medir

    banda util 141-171  (largura 7)  piso escolhido 156 -- o CENTRO dela

Sete pisos contiguos aceitos, tres deles sustentados por **uma escala so**. O M-E, com passo 10,
reportava `150-170`; o passo 5 acha o `141` e o `146` que ele nao experimentou. A banda e larga e
**nao** dispara o aviso de fragilidade.

### 2. A altura de faixa da `barra_direita` — e a convencao que a resolve

O plano manda o SUMMARY registrar a altura de faixa e diz *"ela tem de ser **10** (M-K); se sair
17, o recorte pegou o icone seguinte"*. Medido com `segmentar_glifos_no_brilho` sobre as **cinco**
fixturas de `barra_direita`, nos pisos 180/185/190:

| medida | valor exclusivo (`fim - inicio`) | valor inclusivo (`+1`) |
| ------ | -------------------------------- | ---------------------- |
| faixa do recorte INTEIRO | **16** | 17 |
| faixa do MIOLO, sem os dois icones de ponta | **9** | **10** |

**Os dois numeros do plano estao certos e descrevem coisas diferentes, em convencoes diferentes.**
O `17` do M-O e a faixa do recorte inteiro na convencao inclusiva — e o M-O ja dizia que isso e
*"correto e previsto: a regra 1 descarta as pontas por largura e so entao a faixa e recomputada"*.
O `10` do M-K e a faixa do **miolo**, tambem inclusiva. Na convencao **exclusiva** do codigo
(`larguras_de_molde`, que e a que a peneira do `01-05` vai usar) eles valem **16** e **9**.

**O retangulo `1540,1358 160x34` esta correto** e nao pega o icone seguinte. As larguras batem
caractere por caractere com a verdade de campo nas quatro fixturas de campo — por exemplo, a
Faerlina de 00h45 (`13.160.684`, dez caracteres):

    piso 185  altura de faixa 16  12 corridas
    larguras (convencao EXCLUSIVA): [14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]
                                     ^^ icone   10 caracteres no meio     ^^ icone

**Quem escrever a guarda de altura do `01-05` precisa declarar a convencao.** Uma guarda escrita
contra o `10` rodando na convencao do codigo (onde vale 9) recusaria todo molde legitimo, e o modo
de falha seria um cortador que nunca corta nada.

### 3. O criterio 4, medido antes de o portao ser escrito

Literais inteiros dos onze numeros distintivos do spike na **arvore de sintaxe** de todo
`l2scanner/*.py`, mais os tres ambiguos nos modulos da renda: **zero ocorrencias**. O portao nasce
verde — e por isso o controle positivo e obrigatorio.

Os mesmos numeros por **texto cru** (`(?<!\d)N(?!\d)`), depois de este plano escrever:

| numero | 1368 | 1230 | 1200 | 736 | 520 | 470 | 246 | 210 | 190 | 170 | 26 |
| ------ | ---- | ---- | ---- | --- | --- | --- | --- | --- | --- | --- | -- |
| ocorrencias | 4 | 0 | 1 | 4 | 2 | 4 | 8 | 11 | 10 | 6 | 58 |

**108 ocorrencias, e nenhuma delas e codigo** — todas em comentario ou docstring, inclusive uma
linha de `calibrar_mercado.py` cuja frase e literalmente *"Escrever 210 no fonte seria transformar
uma medicao numa constante"*, e o proprio `calibrar_renda.py`, que cita `246,736` e `236,750` para
explicar por que nao comeca sem saber de quem e a tela. **O M14 do plano contava 21; hoje sao 108**
— este plano *aumentou* a prosa, o que reforca a refutacao em vez de enfraquece-la. Um portao por
`grep` nasceria vermelho e seria "consertado" apagando comentarios que valem mais que ele.

## O ACHADO — e ele nao foi pintado de verde

O plano mandava, no quarto caso da Prova 3, deslocar o retangulo por poucos pixels de modo a cortar
um digito, com a expectativa de **recusa**, e com a instrucao explicita de que um numero seria um
**achado** e nao um teste a forcar.

**Ela devolve um numero, e ele esta errado.** Medido sobre `montagem_da_janela.png`, retangulo do
EXP `0,1368 520x24`, piso 160, deslocando a borda esquerda para dentro (verdade de campo:
`8,0012%` = `80012`):

| deslocamento | resultado | escalas |
| ------------ | --------- | ------- |
| ate +82 | `80012` (`8.0012%`) — **certo** | 1–2 |
| +83 | recusa por discordancia entre escalas | — |
| **+84** | **`30012`** (`3.0012%`) — **ERRADO** | 1 |
| **+85** | **`10012`** (`1.0012%`) — **ERRADO** | 1 |
| **+86** | **`10012`** (`1.0012%`) — **ERRADO** | **2** |
| +87 e alem | recusa por gramatica | — |

**Ha uma janela de TRES PIXELS em que a leitura fabrica um EXP gramaticalmente perfeito e errado.**
E o `+86` e o pior dos tres: **as duas escalas concordam no numero errado**, entao o cruzamento
nao pega — e o cruzamento e a unica guarda que resta depois da gramatica.

**Isto contradiz parcialmente uma afirmacao do `01-01`.** A docstring de `_cruzar_as_escalas` diz
que a regra da abstencao *"continua CORRETA E OBRIGATORIA para o EXP e para o nivel"* e que ela
falhou **so** na adena, porque a adena tem um sosia gramatical adjacente. Medido aqui: **o EXP tem
o mesmo modo de falha, por RECORTE em vez de por campo vizinho.** Cortar o primeiro digito
transforma `8` em `3` e depois em `1`, e o que sobra passa na gramatica inteira. **O sosia nao
precisa estar ao lado; basta o corte fabricar um.**

**Onde isto importa e o que o mitiga:** a guarda que existe para este caso e a de **recorte** e nao
a de leitura — o retangulo vem do calibrador, o calibrador desenha a imagem de conferencia, e o
olho do usuario e quem ve que o `8` esta cortado. A janela e estreita (3 px de 520), mas ela cai
exatamente onde uma janela levemente movida cairia. Registrado em teste, com a tabela inteira
presa, para que a proxima pessoa que mexer no recorte ou no cruzamento veja que existe uma faixa
onde a leitura mente.

**O que este caso cobre e o que nao cobre:** um campo (o EXP), uma fixtura, um piso, e deslocamento
so da borda esquerda. Nao mede a borda direita, nem o deslocamento vertical, nem os outros dois
campos. Uma conclusao geral a partir dele seria a mesma sorte que o M-N ja custou a esta fase.

## Deviations from Plan

### 1. [Sequenciamento — instrucao do coordenador] A Tarefa 2 foi executada pela metade

**Achado durante:** a conferencia de precondicao, antes da Tarefa 2.

`renda_leitura._glifos_do_numero` nao existe neste worktree e nao vai existir: ele e escrito pelo
`01-05`, em paralelo, noutro worktree. O coordenador confirmou o sequenciamento e mandou parar na
fronteira. Feito: a metade de OCR da varredura (EXP e nivel) esta inteira e testada; a metade de
glifo (a `barra_direita`) nao foi escrita, e **nenhuma peneira propria** foi criada.

**Nao aplicado, e a razao:** o coordenador sugeriu, como saida, "classificar por forma da
segmentacao apenas, sem `ler_glifos`". Isso conflaciona duas coisas: `ler_glifos` (o leitor de
valor, que precisa de moldes) e `_glifos_do_numero` (a peneira de forma). A saida declarada no
plano para o caso sem moldes e sobre a primeira; classificar por forma **e** a segunda, e
escreve-la aqui seria exatamente a segunda peneira que a tarefa existe para nao criar — com o
agravante da divergencia de convencao do M-P. Preferiu-se parar e relatar.

### 2. [Rule 2 — funcionalidade critica ausente] A altura de faixa da adena passou a sair na tela

**Achado durante:** a conferencia final contra o `<threat_model>`.

A ameaca **T-01-61** pede que a varredura mostre a altura de faixa medida do recorte escolhido, e
ela estava dentro da varredura de glifo que ficou de fora. Mas a medicao **nao precisa da peneira**
— `segmentar_glifos_no_brilho` e so cv2. Acrescentada como `medir_a_forma_da_adena`, que **mede e
nao classifica**, com a convencao declarada e um teste afirmando que ela nao devolve veredicto
nenhum. Mais o aviso de run largo no meio, com controle negativo e positivo.

**Commit:** `e64f7ad`.

### 3. [Rule 3 — bloqueio direto da mudanca] O tripwire de escritores do `calibration.json` disparou

**Achado durante:** a suite completa, apos a Tarefa 3.

`tests/test_calibrar_nao_apaga_identidades.py` mantem `MODULOS_QUE_GRAVAM`, o conjunto de quem
grava uma `Calibracao`, e a mensagem dele diz: *"um escritor novo do calibration.json precisa de
olhos humanos, porque foi um escritor que apagou 13 moldes de glifo em 2026-08-30"*.

**O portao funcionou como projetado.** `calibrar_renda.py` foi inscrito, com o que se conferiu
antes escrito ao lado (carrega antes de mutar; muta por copia com substituicao; esta preso por
`test_calibrar_renda_nao_apaga_nada.py`; nao importa o acervo). O arquivo **nao** esta em
`files_modified` deste plano — a mudanca e aditiva, e a mesma linha vai precisar receber
`calibrar_renda_moldes.py` do `01-05`. **Possivel conflito de merge de uma linha; sinalizado aqui.**

**Commit:** `42ef15e`.

### 4. [Ambiente] Dois portoes de `grep` do plano nao podiam ser implementados como escritos

Os criterios de aceitacao pedem `grep -v '^\s*#' | grep -c "intersecao_das_bandas"` == 0 e o mesmo
para `_cruzar_as_escalas` >= 1. Medido: o primeiro **nasce vermelho**, porque `intersecao_das_bandas`
aparece dentro da propria **docstring** que explica por que a funcao nao existe — e `grep -v '^\s*#'`
remove comentario, nao docstring. O portao pediria que alguem apagasse a refutacao para satisfaze-lo,
que e o oposto do que o plano quer ("uma funcao que some sem explicacao volta em seis meses; uma
refutacao escrita nao volta").

Implementados como portoes de **identificador na arvore de sintaxe**: o nome nao pode existir como
codigo, e um caso separado exige que ele **exista** como prosa citando M9 e M-E. E a mesma correcao
de forma que o M14 obrigou no criterio 4, uma escala abaixo.

## Como cada criterio de aceitacao foi verificado

| criterio | resultado |
| -------- | --------- |
| `pytest tests/test_calibrar_renda_bat.py` verde, >= 6 casos | **9 passed** |
| `ast.parse(calibrar_renda.py)` sem erro | verde |
| `--so-medir` sai 0, imprime a varredura, fixtura **inalterada** | exit 0, md5 identico antes/depois |
| o mesmo sem `--personagem` sai != 0, sem captura antes | exit 1, mensagem propria |
| `--partir-de` sem `--so-medir` sai != 0, nomeia a recusa | exit 1, nomeia a combinacao |
| sugestao do vizinho oferecida **e** anunciada em texto | verde (3 casos + a rodada inteira) |
| nenhum `Regiao(...)` com 4 inteiros literais; nenhum piso de literal | verde, por AST |
| `carregar` antes de mutar e de gravar, por AST | verde |
| `pytest tests/test_calibrar_renda.py` verde no Python global, **0 skip** | **55 passed**, 0 skipped, 0,5 s |
| tres veredictos DISTINTOS entre si | verde |
| discordancia FORA + controle de concordancia DENTRO | verde |
| abstencao **DENTRO** (M-D), com a mensagem do nivel da Faerlina | verde |
| `escolher_o_piso` devolve o do meio e nao o primeiro | verde (3 e 5 elementos) |
| largura 1 FRAGIL + **controle** de largura 5 nao-fragil | verde |
| passo de 5 afirmado, com a mensagem citando o 155 | verde |
| `intersecao_das_bandas` == 0 como codigo, refutacao escrita | verde (ver Deviation 4) |
| `_cruzar_as_escalas` usado; sem 2a regex; sem 2a particao | verde |
| nenhuma funcao combina bandas de regioes diferentes | verde, por AST sobre os argumentos |
| as tres provas verdes, **0 skipped** (com a ponte de OCR) | **99 passed**, 0 skipped |
| controle positivo da nao-destruicao | verde — retangulo **e** piso mudaram |
| `grep -c "make_dataclass\|fields(Calibracao)"` >= 2 | **7** |
| controle do PERSONAGEM VIZINHO, sub-chave inclusive | verde (4 casos) |
| renda **depois** tiat: os dois personagens de pe | verde; e o mesmo com a party |
| `grep -c ARQUIVO_CALIBRACAO` >= 1; nada escrito fora de `tmp_path` | verde, afirmado por teste |
| verificador de literais e UMA funcao usada pelos dois lados | verde, afirmado por AST |
| a janela movida afirma o **inteiro** (80012) e o resumo identico | verde |
| suite completa | **4959 passed, 24 skipped** (ver Deferred) |
| `git diff --stat` de mercado/renda_leitura/calibracao/requirements | **vazio** nos quatro |
| `calibration.json` real intocado | intocado (monkeypatch em todo caso) |

**Nao verificado como escrito:** os criterios da varredura de glifo da `barra_direita` (a forma
`[15, 5, 2, ...]`, o par sem-moldes/com-moldes, os dois greps de `_glifos_do_numero`). Eles
dependem da peneira do `01-05`. Ver "O que falta para fechar".

## TDD Gate Compliance

- **Tarefa 2** (`tdd="true"`): executada pela metade por sequenciamento (Deviation 1). A metade
  entregue tem commit `test(01-03)` sem `feat` par, o que e correto — a implementacao veio da
  Tarefa 1 por desenho do plano, e os 55 casos sao amarra sobre ela.
- **Tarefa 3** (`tdd="true"`): os 16 casos de nao-destruicao passaram na primeira rodada, o que a
  regra de fail-fast proibe aceitar. **Investigado por injecao de defeito**, e o resultado esta
  medido:

      por_personagem = {}            (reconstrucao do dicionario)  ->  7 vermelhos
      cal.tiat_chat = None           (clobber de chave de topo)    ->  1 vermelho

  Os 7 sao exatamente os casos do personagem vizinho e da ida e volta. O fonte foi restaurado e
  conferido (`grep -c "DEFEITO INJETADO"` == 0).

## Known Stubs

**Nenhum stub.** Nada nesta rodada devolve valor fixo, lista vazia ou placeholder para simular
funcionamento. A `barra_direita` **nao** e um stub: ela nao e varrida, o calibrador **diz isso em
voz alta** no terminal, imprime a ordem de operacao, e **recusa gravar** (`exit != 0`, nada
escrito) quando um personagem ficaria sem piso naquela regiao. Um usuario nunca recebe uma
calibracao de adena que parece pronta e nao esta.

## O que falta para fechar o `01-03`

Tudo abaixo depende de **um** artefato: `renda_leitura._glifos_do_numero`, do `01-05` Tarefa 1.
Quando ele estiver na arvore, a rodada de fechamento e curta e esta inteiramente especificada:

1. **A varredura da `barra_direita`** — por piso: `mascara_de_numero` -> `segmentar_glifos_no_brilho`
   -> **`_glifos_do_numero` IMPORTADA** (o import e a unica linha nova de acoplamento). Dentro da
   banda quando a peneira aceita a forma; fora quando recusa, com o motivo na linha.
2. **O par sem-moldes / com-moldes** — sem `renda_moldes_da_barra` a banda **nao** sai vazia (a
   forma decide sozinha) e `ler_glifos` **nao** e chamada; com moldes o valor entra como coluna
   **informativa** e o dentro/fora **nao muda**.
3. **Os dois greps** — `def _glifos_do_numero` em `calibrar_renda.py` == 0, e `_glifos_do_numero`
   como identificador >= 1.
4. **O `faltando` do caminho de escrita** deixa de barrar o primeiro personagem: hoje, um
   personagem sem piso de `barra_direita` em disco faz a rodada recusar. Com a varredura, o piso
   sai medido.

**Nao precisa de mudanca:** o retangulo, o carimbo de geometria, a nao-destruicao, o `.bat`, o
criterio 4 e a medicao de forma — todos fechados e testados.

Duas notas para quem fizer essa rodada, as duas medidas aqui:

- **Declare a convencao de largura.** A peneira roda na **exclusiva** (`fim - inicio`): digito
  4/5/6, virgula 1, icones 14/15. O criterio de aceitacao do plano cita a sequencia
  `[15, 5, 2, 5, 5, 5, 2, 5, 5, 5, 16]`, que esta na convencao **inclusiva** — ela vale
  `[14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]` no codigo. Traduza antes de escrever a assercao.
- **A guarda de altura de faixa e 9 exclusiva (10 inclusiva) para o miolo**, e 16 exclusiva
  (17 inclusiva) para o recorte inteiro com os icones dentro.

## Deferred Issues (fora do escopo deste plano)

- **`tests/test_agenda.py` aborta a sessao do pytest.** Pre-existente e sem relacao com esta fase,
  ja documentado no `01-01-SUMMARY.md`: ele levanta `KeyboardInterrupt` de proposito para sair do
  laco. Conferido nesta rodada — sozinho ele passa (`87 passed`), mas encerra a sessao. A suite
  completa se roda em duas partes; os 145 casos dele nao estao nos 4959 acima. **Nao consertado**,
  por instrucao.
- **Os 24 skips da suite completa** sao de arquivos de OCR de outras features, pre-existentes.
  Nenhum arquivo desta rodada pula: os quatro que nao precisam de OCR rodam no Python global, e o
  quinto (`test_a_janela_movida...`) usa o idioma de skip da casa e sai **0 skipped** com a ponte
  `PYTHONPATH=".;<repo>/.venv/Lib/site-packages"`.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: correctness | `l2scanner/renda_leitura.py` | O EXP tem o mesmo modo de falha por substituicao que a docstring de `_cruzar_as_escalas` atribui **so** a adena — medido: uma janela de 3 px de deslocamento do recorte fabrica `30012`/`10012` no lugar de `80012`, e num dos tres as **duas** escalas concordam no erro. A docstring daquele modulo precisa ser corrigida por quem for mexer nela (arquivo do `01-05` nesta onda; nao tocado aqui). |
| threat_flag: merge | `tests/test_calibrar_nao_apaga_identidades.py` | `MODULOS_QUE_GRAVAM` recebeu `calibrar_renda.py`; o `01-05` vai precisar acrescentar `calibrar_renda_moldes.py` na mesma linha. Conflito de merge de uma linha, aditivo dos dois lados. |

## Self-Check: PASSED

Arquivos conferidos em disco: `l2scanner/calibrar_renda.py`, `calibrar-renda.bat`,
`tests/test_calibrar_renda.py`, `tests/test_calibrar_renda_bat.py`,
`tests/test_calibrar_renda_nao_apaga_nada.py`, `tests/test_nenhum_numero_do_spike_no_fonte.py`,
`tests/test_a_janela_movida_e_consertada_pelo_calibrador.py`, e este SUMMARY.

Commits conferidos em `git log`: `c97f73f`, `be89340`, `42ef15e`, `e64f7ad`.

`STATE.md` e `ROADMAP.md` **nao** foram tocados, por instrucao: worktrees paralelos conflitam
naqueles contadores, e este SUMMARY e o artefato canonico da rodada.
