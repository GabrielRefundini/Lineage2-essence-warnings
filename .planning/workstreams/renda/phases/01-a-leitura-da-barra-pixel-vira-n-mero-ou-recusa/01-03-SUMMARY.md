---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 03
workstream: renda
subsystem: calibracao-da-renda
status: complete
tags: [calibracao, nao-destruicao, varredura-de-piso, criterio-4, bat, glifo, M-U]
requires:
  - l2scanner.renda_leitura (_cruzar_as_escalas, _glifos_do_numero, resolver_o_limite_de_glifo, decimos_de_milesimo, recortar, MOTIVO_*)
  - l2scanner.calibracao (renda_por_personagem, REGIOES_DA_RENDA, PISO_DE_BRILHO_*_DA_RENDA)
  - l2scanner.calibrar (_selecionar_regiao, _gravar_conferencia)
  - l2scanner.mercado_leitura (mascara_de_numero, numero_valido, segmentar_glifos_no_brilho, ler_glifos)
  - l2scanner.mercado_visao (glifos_de_calibracao)
provides:
  - l2scanner.calibrar_renda (calibrar_renda, varrer_o_piso, varrer_a_forma, classificar_a_leitura, resumir_a_banda_util, escolher_o_piso, grade_de_pisos, medir_a_forma_da_adena, descrever_a_forma, avisar_sobre_o_limite_herdado, ordem_de_operacao)
  - l2scanner.renda_leitura (limite_de_arranque, resolver_o_limite_de_glifo, LIMITE_VEIO_DOS_MOLDES, LIMITE_VEIO_DO_ARRANQUE) -- a resolucao do limite, agora no modulo PURO
  - calibrar-renda.bat
  - O PRIMEIRO ESCRITOR de Calibracao.renda_por_personagem
affects:
  - tests/test_calibrar_nao_apaga_identidades.py (inscricao no tripwire MODULOS_QUE_GRAVAM)
  - l2scanner/calibrar_renda_moldes.py (o `limite_de_arranque` mudou de casa; a chamada passou a ser `resolver_o_limite_de_glifo`)
  - l2scanner/renda_leitura.py (a docstring de `_cruzar_as_escalas` corrigida por medicao)
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
    - l2scanner/renda_leitura.py (rodada de fechamento)
    - l2scanner/calibrar_renda_moldes.py (rodada de fechamento)
decisions:
  - "A varredura da `barra_direita` classifica pela FORMA das corridas, pela peneira `_glifos_do_numero` IMPORTADA do modulo puro; `grep -c 'def _glifos_do_numero'` no calibrador da 0"
  - "A banda util do EXP da Faerlina, medida com passo 5: 141-171, largura 7, piso do centro 156"
  - "A altura de faixa do recorte `1540,1358 160x34` e 16 EXCLUSIVA (17 inclusiva); o miolo sem os icones e 9 exclusiva (10 inclusiva), que e o `10` do M-K"
  - "ACHADO: ha uma janela de 3 px (+84..+86) em que a leitura do EXP FABRICA numero errado, e em +86 as duas escalas concordam no erro -- a docstring de `_cruzar_as_escalas` foi corrigida com a tabela"
  - "`limite_de_arranque` desceu para `renda_leitura` e ganhou `resolver_o_limite_de_glifo`, que devolve tambem a ORIGEM do limite: copia-lo para o segundo calibrador criaria duas regras de arranque, e importar um calibrador do outro esta proibido por desenho"
  - "O aviso do M-U tem DOIS testes: arranque > limite herdado E a corrida que sobra ainda cabe como digito (`FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO`). Sem o segundo ele dispararia no caso M-N e mandaria deixar quieto um retangulo de fato errado"
  - "O piso da adena sai MEDIDO, e o `faltando` deixou de barrar o primeiro personagem"
  - "`calibrar_renda.py` inscrito em MODULOS_QUE_GRAVAM do tripwire de identidades, com a conferencia escrita ao lado"
metrics:
  duration: ~2 sessoes (a segunda so para a fronteira da peneira)
  completed: 2026-09-02
actuals:
  tokens: 63000
  tasks: 3
  commits: 8
---

# Phase 01 Plan 03: O calibrador da renda — Summary

Um calibrador que carrega o `calibration.json` inteiro antes de tocar nele, marca as tres regioes
da renda **por personagem** com a sugestao vinda do disco, varre o piso de brilho de 5 em 5 com
**tres** veredictos em vez de dois, varre a adena pela **forma das corridas** com a peneira do
`01-05` **importada** — e sem molde nenhum, que e a estreia de todo usuario —, e prova por teste
que uma rodada da Faerlina deixa a Yazalaque byte a byte identica. Mais o criterio 4 do roadmap
virado portao de arvore de sintaxe, e o aviso que impede a recusa da peneira de culpar um
retangulo inocente (M-U).

## STATUS: COMPLETO — em DUAS rodadas, e a fronteira entre elas foi respeitada

**Primeira rodada (2026-09-02, madrugada):** tudo que nao dependia da peneira de forma. Ela parou
**exatamente** na fronteira de `renda_leitura._glifos_do_numero`, que e escrita pela Tarefa 1 do
`01-05` — o plano da **mesma onda 2** —, e **nao escreveu uma peneira propria para destravar**. A
precondicao declarada da Tarefa 2 foi conferida no inicio e no meio da execucao:

    grep -c "def _glifos_do_numero" l2scanner/renda_leitura.py  ->  0

**Segunda rodada (2026-09-02, tarde):** o `01-05` fechou e a peneira esta na arvore. A metade que
faltava foi escrita **importando** aquela peneira. `grep -c "def _glifos_do_numero"` em
`l2scanner/calibrar_renda.py` continua **0**; o identificador aparece **4 vezes como codigo**.

**A recusa da primeira rodada foi o que tornou a segunda barata, e isso e um resultado.** As
larguras deste projeto vivem em **duas convencoes** (M-P): `larguras_de_molde` mede `fim - inicio`
(**exclusiva** — digito 4/5/6, virgula 1, icones 14/15) e o `01-MEDICOES-DE-CAMPO.md` relata
`fim - inicio + 1` (**inclusiva** — 5/6/7, 2, 15/16). Uma peneira escrita as pressas contra a
convencao errada recusa o digito mais largo e aceita icone estreito, calada nos dois sentidos. A
segunda rodada nao teve de descobrir isso: ela leu a assinatura e o contrato de retorno da peneira
verdadeira, **traduziu a sequencia do criterio de aceitacao** (que esta na convencao inclusiva) e
seguiu.

O que a segunda rodada entregou esta na secao **"A rodada de fechamento"**, no fim.

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

### 1. [Sequenciamento — instrucao do coordenador] A Tarefa 2 foi executada pela metade — **FECHADA na rodada seguinte**

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

### 3b. [Rule 3 — bloqueio direto da mudanca, rodada de fechamento] O arranque do limite morava no calibrador ERRADO

**Achado durante:** a Tarefa 2, metade de glifo.

A varredura de forma precisa de um limite **sem moldes** — senao `_glifos_do_numero` recusa com
`limite=None` e a banda sai vazia na estreia, que e exatamente o defeito que o plano manda nao ter.
`limite_de_arranque` ja existia, ja estava medido, e morava em `calibrar_renda_moldes` — e o plano
**proibe seta de codigo entre os dois calibradores** por decisao explicita.

**Copiar era pior.** Duas regras de arranque para uma so fonte e a mesma familia de defeito que a
peneira unica existe para nao ter, uma peca abaixo. A regra desceu para `renda_leitura`, o modulo
**puro** que os dois ja importam: ela continua existindo **uma vez** e as setas continuam
ferramenta -> puro. Junto desceu `resolver_o_limite_de_glifo`, que devolve tambem **a origem** do
limite — e sem a origem o aviso do M-U nao teria como existir.

**Commit:** `8d12ddd`.

### 3c. [Rule 2 — funcionalidade critica ausente, rodada de fechamento] A recusa da peneira culpava o retangulo inocente

**Achado durante:** a leitura do `01-05-RODADA-DE-MOLDES.md`, achado M-U, e reconferido em pixel.

A peneira recusa um recorte correto quando o conjunto de moldes ainda e estreito, e a mensagem diz
*"o recorte pegou o campo vizinho junto"* — mandando o usuario remarcar um retangulo que nao tem
defeito. Medido deste lado, com o limite travado em 4 sobre as cinco fixturas: **duas ficam com a
banda inteiramente vazia.** Um calibrador que apenas repetisse a recusa da peneira estaria **dando
autoridade a uma atribuicao errada**, e isso e pior que silencio.

`avisar_sobre_o_limite_herdado` foi acrescentado com **dois** testes (ver a secao propria), e o
segundo deles nasceu de um caso vermelho que teria produzido o dano inverso.

**Commit:** `fdbb3bc`.

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

**E aconteceu uma TERCEIRA vez na rodada de fechamento, na direcao oposta.** O portao
`grep -c "def _glifos_do_numero" == 0` nasceu **vermelho** porque um comentario novo dizia *"este
arquivo nao contem `def _glifos_do_numero`"* — a frase que explica o portao carregava a assinatura
que o portao proibe. Desta vez o conserto foi **reescrever a frase** (ela nao precisa da assinatura
literal para dizer o que diz) e afirmar os DOIS: a ausencia na arvore de sintaxe, que e o que de
fato se proibe, e a ausencia no texto cru, que e o que o plano mede. Fica o padrao, ja com tres
ocorrencias nesta fase: **um criterio escrito como `grep` mede prosa junto com codigo, e o
resultado e sempre pressao para apagar a explicacao.**

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

**Os criterios da varredura de glifo, verificados na rodada de fechamento:**

| criterio | resultado |
| -------- | --------- |
| a forma esperada DENTRO da banda | verde — com as larguras **traduzidas** para a convencao exclusiva (`[14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]`); o `[15, 5, 2, ...]` do plano e a inclusiva |
| CONTROLE: contagem de corridas diferente FORA, mesmo com string lida | verde — e o valor sai `None`, porque a leitura so acontece **depois** do veredicto |
| sem moldes a banda NAO sai vazia | verde (3 pisos) |
| sem moldes `ler_glifos` NAO e chamada | verde — espionando a funcao de **producao**, nao o injetavel |
| sem moldes a saida traz a ordem de operacao | verde — `calibrar-renda-moldes.bat`, `--so-medir`, "O VALOR NAO FOI LIDO" |
| CONTROLE com moldes: valor informativo **e** banda identica | verde |
| `grep -c "def _glifos_do_numero"` no calibrador == 0 | **0** (por AST **e** por texto cru) |
| `_glifos_do_numero` usado como identificador >= 1 | **4** |
| a saida nomeia o metodo como GLIFO | verde — e nomeia o de OCR **negado**, para o usuario nao comparar os dois pisos |
| nenhum caminho varre a `barra_direita` pelos quatro desfechos | verde, por AST sobre as funcoes de forma |
| a altura de faixa medida do recorte escolhido (T-01-61) | verde — 9 peneirada / 16 bruta, com a convencao na saida |
| suite completa | **5141 passed, 24 skipped** (`tests/test_agenda.py` ignorado) |

## TDD Gate Compliance

- **Tarefa 2** (`tdd="true"`): a metade de OCR foi entregue na primeira rodada com commit
  `test(01-03)` sem `feat` par, o que e correto — a implementacao veio da Tarefa 1 por desenho do
  plano, e os casos sao amarra sobre ela. A metade de **glifo** fechou na segunda rodada com o par
  completo: `feat(01-03)` para a varredura, `test(01-03)` para os 25 casos novos.

  **A regra de fail-fast foi exercida e pagou.** Os 25 casos nao passaram na primeira rodada:
  **tres ficaram vermelhos**, e dois deles eram defeito de producao e nao de teste.

      CONTROLE do icone no meio (forma do M-N)  ->  o aviso do M-U DISPAROU
      portao do `grep` da peneira unica         ->  a prosa carregava a assinatura

  O primeiro e o mais serio: com so a pergunta do limite, o aviso teria dito *"nao remarque o
  retangulo"* sobre um retangulo de fato errado — o dano do M-U **virado do avesso**. A segunda
  pergunta (a corrida ainda cabe como digito?) nasceu desse vermelho. O terceiro vermelho era do
  proprio teste (`Calibracao()` sem argumentos) e foi corrigido no teste.
- **Tarefa 3** (`tdd="true"`): os 16 casos de nao-destruicao passaram na primeira rodada, o que a
  regra de fail-fast proibe aceitar. **Investigado por injecao de defeito**, e o resultado esta
  medido:

      por_personagem = {}            (reconstrucao do dicionario)  ->  7 vermelhos
      cal.tiat_chat = None           (clobber de chave de topo)    ->  1 vermelho

  Os 7 sao exatamente os casos do personagem vizinho e da ida e volta. O fonte foi restaurado e
  conferido (`grep -c "DEFEITO INJETADO"` == 0).

## Known Stubs

**Nenhum stub, nas duas rodadas.** Nada aqui devolve valor fixo, lista vazia ou placeholder para
simular funcionamento.

A `barra_direita` deixou de ser a fronteira aberta: ela e varrida, classificada e o piso dela sai
medido. E a coluna de **valor** vazia quando nao ha moldes **nao** e um stub — o calibrador diz em
voz alta que o valor nao foi lido, diz que a banda acima e de FORMA e vale, e imprime a ordem de
operacao. Um usuario nunca recebe uma calibracao de adena que parece pronta e nao esta, nem o
contrario: uma banda de forma boa apresentada como se fosse leitura confirmada.

## A rodada de fechamento — a varredura de forma da `barra_direita`

Os quatro itens que a primeira rodada deixou especificados foram executados exatamente como
escritos, e as duas notas que ela deixou para quem fizesse a rodada foram as duas que evitaram
defeito.

### 1. `varrer_a_forma` — a curva de glifo, com a peneira IMPORTADA

Uma linha por piso, e a linha carrega o que o usuario precisa comparar com a tela: o piso, as
larguras cruas, a **faixa PENEIRADA**, a contagem de corridas do numero, o limite **e de onde ele
veio**, e o valor quando houver moldes. A classificacao e de `_glifos_do_numero`, importada — a
unica linha nova de acoplamento, como previsto.

`medir` e `ler_valor` sao a mesma fronteira que `ler_escalas` ja era na varredura de OCR: os casos
rodam sem pixel e sem disco. Eles nao sao atalho de teste — sao a separacao entre o laco que olha
pixel e as funcoes que decidem.

**A banda reusa `resumir_a_banda_util`, e isso e deliberado.** `LinhaDaForma` expoe
`escalas_que_sustentaram` devolvendo **sempre a tupla vazia**, com a razao escrita ao lado: nesta
curva nao ha escala nenhuma, quem aceita e a forma sozinha. Duas definicoes de "banda contigua"
seriam duas regras de centro, e o piso gravado de um campo deixaria de ser comparavel com o do
outro. O efeito colateral e correto de graca: o aviso "a banda inteira foi sustentada por uma
escala so" **nao dispara** neste campo, porque aqui nao existe segunda opiniao a perder.

### 2. O par sem-moldes / com-moldes — e o teste espiona a funcao de PRODUCAO

Sem `renda_moldes_da_barra` a banda **nao** sai vazia e `ler_glifos` **nao** e chamada. O caso que
afirma a nao-chamada espiona `cr.ler_glifos` por `monkeypatch`, e nao o `ler_valor` injetavel: com
o injetavel ele mediria o proprio teste.

Com moldes, o valor entra como coluna **informativa** e o dentro/fora **nao muda** — afirmado
comparando as duas bandas com moldes cuja largura maxima e a mesma que o arranque mediria, de modo
que a **unica** coisa que difere entre as duas varreduras e a coluna de valor.

### 3. Os dois greps, medidos

    grep -c "def _glifos_do_numero" l2scanner/calibrar_renda.py             ->  0
    grep -v '^\s*#' l2scanner/calibrar_renda.py | grep -c "_glifos_do_numero" ->  4

O portao do plano e um `grep`, e um `grep` nao distingue codigo de prosa — foi preciso **reescrever
uma frase de comentario** que carregava a assinatura literal, senao o portao nasceria vermelho
pedindo que alguem apagasse a explicacao. O teste afirma os dois: a ausencia na **arvore de
sintaxe** (o que de fato se proibe) e a ausencia no texto cru (o que o plano mede).

### 4. O `faltando` deixou de barrar o primeiro personagem

A adena entra no mesmo dicionario de bandas do caminho de escrita, e o piso dela sai **medido** em
vez de exigido do disco. Uma primeira calibracao completa agora e possivel numa rodada so.

---

## As medicoes da rodada de fechamento

Todas feitas nesta arvore, contra as fixturas versionadas. Nenhuma copiada de documento.

### A altura de faixa: **9 exclusiva**, e o `10` do plano e o INCLUSIVO

O criterio de aceitacao do plano diz *"Ela tem de ser **10** (M-K)"*. Medido com a peneira sobre as
**cinco** fixturas de `barra_direita`, nos pisos 181, 186 e 191 — quinze medicoes:

| medida | exclusiva (`faixa[1] - faixa[0]`) | inclusiva (`+1`) |
| ------ | --------------------------------- | ---------------- |
| faixa BRUTA (com os icones dentro) | 16 | 17 |
| faixa PENEIRADA (depois do descarte) | **9** | 10 |

**Invariavel nas quinze.** Uma guarda escrita contra `10` rodando na convencao do codigo recusaria
**todo** molde legitimo desta barra, e o modo de falha seria um cortador que roda, sai com codigo 0
e nunca corta nada. A saida do calibrador imprime os dois numeros com a convencao declarada, e um
teste afirma que os dois estao la — dar so um deles manda quem for comparar com o documento de
campo comparar com a convencao errada.

### O centro da banda e o que salva a escolha — e o arranque tem um SEGUNDO ponto cego

Varrendo de 5 em 5 de 1 a 254, **sem moldes** (o estado da primeira rodada de todo usuario):

| fixtura | banda de forma | piso escolhido (o CENTRO) |
| ------- | -------------- | ------------------------- |
| `aba_para_calibrar_f000` | 166-201 | **186** |
| `campo_faerlina_f000` | 166-201 | **186** |
| `campo_yazalaque_f001` | 161-201 | **181** |
| `segundo_cenario_faerlina` | 171-201 | **186** |
| `segundo_cenario_yazalaque` | 166-201 | **186** |

As cinco caem **dentro da banda de glifo medida em campo** (180-190, M-J). Mas repare que a banda
de **forma** comeca antes de 180 — e a razao e um ponto cego novo do `limite_de_arranque`, medido
aqui e escrito na docstring dele: **num piso baixo demais glifos vizinhos COLAM**, e o arranque
adota a largura do par colado (10, 11, 12). A forma passa, com **uma corrida a menos** do que o
numero tem caracteres. A regra do **centro** — que existia por outro motivo, a folga dos dois lados
— e o que impede aquele piso de ser escolhido. Ela ganhou uma segunda justificativa medida.

Com o conjunto de moldes **completo** (limite 6) a banda encolhe para 171-201 / 176-201 / 181-201 e
os centros vao para 186-191; a faixa peneirada continua 9 em toda a banda.

### O M-U reproduzido DESTE lado, sobre pixel de campo

Travando o limite em 4 — o que a ordem alfabetica do cortador produz — sobre as cinco fixturas:

| fixtura | banda de forma com limite 4 |
| ------- | --------------------------- |
| `aba_para_calibrar_f000` | 181-201 |
| `campo_faerlina_f000` | **so 201** — as recusas de 181/186/191 dizem "o recorte pegou o campo vizinho junto" |
| `campo_yazalaque_f001` | 176-201 |
| `segundo_cenario_faerlina` | **VAZIA** |
| `segundo_cenario_yazalaque` | **VAZIA** |

**Duas das cinco ficam sem banda nenhuma, e a mensagem manda remarcar um retangulo que esta
correto.** E o M-U inteiro, do lado do calibrador de pisos em vez do cortador. O retangulo daquelas
duas e o mesmo que produz banda larga com o limite certo.

---

## O aviso do M-U, e por que ele tem DUAS perguntas e nao uma

`avisar_sobre_o_limite_herdado` so dispara quando **as duas** respondem sim:

1. **O limite e estreito demais para este recorte?** O limite dos moldes e a maior largura do
   conjunto **ja cortado**; o arranque e a maior largura do **miolo deste recorte**. Arranque maior
   que limite quer dizer que ha aqui um glifo mais largo que qualquer molde gravado.
2. **A corrida que sobra ainda PODE ser um digito?** Se ela tem largura de **icone**, o recorte
   pegou mesmo o campo vizinho — e ai a peneira esta certa e o conserto **e** o retangulo.

**A segunda pergunta nasceu de um teste VERMELHO, e sem ela o aviso teria o dano do M-U virado do
avesso.** A primeira versao tinha so a pergunta 1, e o controle com um icone no meio — a forma
medida do retangulo refutado pelo M-N — disparou o aviso, que teria dito ao usuario *"nao remarque
o retangulo"* sobre um retangulo de fato errado. O discriminador usa
`FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO`, a **mesma** constante que o aviso de recorte contaminado ja
usava, pela mesma medicao: icones de ponta valem 14 e 15 e o digito mais largo desta fonte vale 6,
entao metade do icone (7,0-7,5) separa as duas populacoes com folga de um pixel.

**Nenhum numero desta fonte foi escrito para fazer a comparacao** — os dois lados sao derivados: um
dos moldes, o outro do proprio recorte.

---

## `limite_de_arranque` mudou de casa, e a razao e a mesma da peneira unica

A varredura de forma precisa de um limite **sem moldes**, senao `_glifos_do_numero` recusa com
`limite=None` e a banda sai vazia na estreia — exatamente o defeito que o plano manda nao ter.
`limite_de_arranque` ja existia e ja estava medido, mas morava em `calibrar_renda_moldes`, e o
plano proibe seta de codigo entre os dois calibradores (decisao explicita: *"eles nao se importam
nem dividem arquivo"*).

**Copiar teria criado duas regras de arranque para uma so fonte** — a mesma familia de defeito que
`_glifos_do_numero` existe para nao ter, uma peca abaixo. A saida que respeita as duas coisas foi
descer a regra para o **modulo puro**, que os dois ja importam: ela continua existindo **uma vez**,
e as setas continuam ferramenta -> puro. `calibrar_renda_moldes` importa o nome de la e nada mais
muda nele.

Junto desceu `resolver_o_limite_de_glifo(moldes, runs) -> (limite, origem)`, que substitui o
`limite_de_glifo_unico(moldes) or limite_de_arranque(runs)` que o cortador tinha inline. **A origem
e o M-U virado assinatura**: sem ela, nenhum dos dois consumidores tem como saber se a recusa que
recebeu veio de um limite herdado ou de um recorte de fato errado.

---

## A correcao da docstring de `_cruzar_as_escalas` — reproduzida antes de escrita

O achado da primeira rodada foi **reproduzido nesta arvore** antes de virar prosa no modulo puro,
sobre `montagem_da_janela.png`, retangulo do EXP `0,1368 520x24`, piso 160, verdade `80012`:

    ate +82  80012 certo (1-2 escalas) | +83 recusa por discordancia
    +84  30012 ERRADO (1 escala) | +85  10012 ERRADO (1 escala)
    +86  10012 ERRADO -- AS DUAS ESCALAS CONCORDAM
    +87 e alem  recusa por gramatica

A docstring dizia que a regra da abstencao *"continua CORRETA E OBRIGATORIA para o EXP"* e que ela
falhou **so** na adena, porque a adena tem um sosia gramatical **adjacente**. As duas metades
estavam certas de menos, e agora a docstring diz o que foi medido: **o EXP tem o mesmo modo de
falha, e o sosia nao precisa estar ao lado — basta o CORTE fabricar um.**

O que **nao** mudou, e vai escrito junto: a regra. Exigir concordancia tambem nao pegaria o `+86`,
e recusaria o nivel da Faerlina para sempre. O que muda e **onde a guarda mora** — ela e do
RECORTE, e quem a exerce e o olho do usuario na imagem de conferencia. E o limite da medicao vai
junto, para ninguem generalizar dela o que ela nao mediu: um campo, uma fixtura, um piso, so a
borda esquerda.

## Deferred Issues (fora do escopo deste plano)

- **`tests/test_janela_de_selecao.py::test_dreno_por_tempo_e_nao_por_numero_de_sondagens` e
  INSTAVEL SOB CARGA, e nao e desta rodada.** Ele mede relogio de parede: o dreno gira por 50 ms e
  o `waitKey` dublado gasta 1 ms por sondagem numa espera OCUPADA, entao a assercao e
  `contador["n"] > 20`. Com a suite inteira competindo por CPU, a preempcao faz cada sondagem
  custar bem mais que 1 ms e menos de 20 cabem no prazo. Medido nesta rodada: **vermelho** numa
  passada da suite completa, **9 passed** rodando o arquivo sozinho logo depois, e **verde** na
  passada seguinte da suite completa. Nada desta rodada toca o caminho dele — os quatro arquivos
  alterados sao `calibrar_renda.py`, `calibrar_renda_moldes.py`, `renda_leitura.py` e
  `tests/test_calibrar_renda.py`, e o teste depende de `l2scanner.calibrar` e
  `l2scanner.calibrar_mercado`. **Nao consertado:** um limiar de contagem preso a tempo de parede
  e um defeito de teste real, mas de outro plano, e mexer nele daqui seria alterar a prova de outra
  feature sem a medicao que a justificou.
- **A ORDEM DO CORTADOR continua alfabetica, e o M-U pede que ela seja por largura decrescente.**
  Este plano fez a metade que e dele: o **calibrador de pisos** nao repete mais a atribuicao errada,
  e a origem do limite agora sai da funcao que o resolve — entao `calibrar_renda_moldes` **ja tem
  em maos** o que precisa para dar a mesma explicacao na recusa dele. O que **nao** foi feito e
  ordenar os recortes por largura maxima de corrida antes de propor, dentro do cortador. Isso e
  mudanca de comportamento de uma ferramenta de outro plano (`01-05`), e o proprio M-U a classifica
  como *"mudanca de plano, nao de rodada"*. **Custo de nao fazer, medido:** rodando em ordem
  alfabetica o usuario fecha **5 rotulos de 11** e recebe tres recusas que culpam o retangulo. O
  conserto de uma linha (ordenar) e o de duas (repetir o aviso do M-U na recusa do cortador) estao
  os dois disponiveis e nenhum foi aplicado aqui.

- **`tests/test_agenda.py` aborta a sessao do pytest.** Pre-existente e sem relacao com esta fase,
  ja documentado no `01-01-SUMMARY.md`: ele levanta `KeyboardInterrupt` de proposito para sair do
  laco. Conferido nas duas rodadas — sozinho ele passa (`87 passed`), mas encerra a sessao. A
  suite completa roda com `--ignore=tests/test_agenda.py`; os casos dele nao estao nos numeros
  acima. **Nao consertado**, por instrucao.
- **Os 24 skips da suite completa** sao de arquivos de OCR de outras features, pre-existentes.
  Nenhum arquivo desta rodada pula: os quatro que nao precisam de OCR rodam no Python global, e o
  quinto (`test_a_janela_movida...`) usa o idioma de skip da casa e sai **0 skipped** com a ponte
  `PYTHONPATH=".;<repo>/.venv/Lib/site-packages"`.
- **A contagem da suite deste worktree e 5116 ANTES desta rodada e 5141 depois** (`+25`, que sao
  exatamente os casos novos: `tests/test_calibrar_renda.py` foi de 55 para 80). O briefing da
  rodada citou **5140** como linha de base, o que nao bate com esta arvore por 24 casos — a
  diferenca e compativel com trabalho paralelo (`01-04`) ja presente na arvore do coordenador e
  ainda nao aqui. **Nao investigado alem disso**, e registrado em vez de arredondado: o que esta
  medido e que nenhum caso pre-existente ficou vermelho e que os skips continuam 24.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| ~~threat_flag: correctness~~ **FECHADO** | `l2scanner/renda_leitura.py` | O EXP tem o mesmo modo de falha por substituicao que a docstring de `_cruzar_as_escalas` atribuia **so** a adena. **Reproduzido nesta arvore na rodada de fechamento** (`+84 -> 30012`, `+85/+86 -> 10012` contra a verdade `80012`, e no `+86` as duas escalas concordam) e a docstring **foi corrigida**, com a tabela e com o limite da medicao escritos. Commit `00a63e4`. |
| ~~threat_flag: merge~~ **RESOLVIDO** | `tests/test_calibrar_nao_apaga_identidades.py` | `MODULOS_QUE_GRAVAM` tem `calibrar_renda.py` e `calibrar_renda_moldes.py`; o `01-05` ja mergeou e a linha esta com os dois. |
| threat_flag: coupling | `l2scanner/renda_leitura.py` | O modulo puro ganhou `limite_de_arranque` e `resolver_o_limite_de_glifo`, que **nao** sao leitura — sao resolucao de geometria consumida por DUAS ferramentas. Elas moram la porque a alternativa era duplicar ou ligar os dois calibradores, e as duas eram piores. Se um terceiro consumidor aparecer, vale a pena avaliar um modulo proprio de geometria da barra em vez de continuar engordando `renda_leitura`. |

## Self-Check: PASSED (nas duas rodadas)

Arquivos conferidos em disco: `l2scanner/calibrar_renda.py`, `calibrar-renda.bat`,
`tests/test_calibrar_renda.py`, `tests/test_calibrar_renda_bat.py`,
`tests/test_calibrar_renda_nao_apaga_nada.py`, `tests/test_nenhum_numero_do_spike_no_fonte.py`,
`tests/test_a_janela_movida_e_consertada_pelo_calibrador.py`, e este SUMMARY.

Da rodada de fechamento, conferidos em disco: `l2scanner/renda_leitura.py`,
`l2scanner/calibrar_renda_moldes.py`.

Commits conferidos em `git log`:

- primeira rodada: `c97f73f`, `be89340`, `42ef15e`, `e64f7ad`
- rodada de fechamento: `8d12ddd` (o limite desce para o modulo puro), `00a63e4` (a docstring do
  cruzamento corrigida), `fdbb3bc` (a varredura de forma), `17faabf` (os 25 casos)

`STATE.md` e `ROADMAP.md` **nao** foram tocados, por instrucao: worktrees paralelos conflitam
naqueles contadores, e este SUMMARY e o artefato canonico da rodada.
