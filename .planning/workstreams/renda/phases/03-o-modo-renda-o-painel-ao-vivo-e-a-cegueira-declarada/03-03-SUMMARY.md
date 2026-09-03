---
phase: 03-o-modo-renda-o-painel-ao-vivo-e-a-cegueira-declarada
plan: 03
subsystem: renda
tags: [LEIT-10, LEIT-11, CONS-01, varredura, piso-de-brilho, M-Y]
status: complete

requires:
  - renda_leitura.ler_os_tres_campos / exp_da_barra / nivel_da_regiao / adena_da_barra (Fase 1)
  - calibrar_renda.PASSO_DA_GRADE_DE_PISOS / BandaUtil / escolher_o_piso (Fase 1)
  - renda_laco.laco_da_renda + o seam `ler_campos=` (03-01)
  - renda_estado.classificar_a_visao / motivo_da_pausa (03-02)
  - renda_console.bloco_da_renda / resumo_da_sessao_da_renda (03-01, 03-02)
provides:
  - l2scanner/renda_leitura.py::ler_um_campo + SUBCHAVE_POR_CAMPO
  - l2scanner/renda_pisos.py::pisos_vizinhos / ALCANCE_EM_PASSOS / PASSO_DA_GRADE
  - l2scanner/renda_laco.py::RECUSAS_SEGUIDAS_PARA_VARRER / TETO_DA_CARENCIA + o seam `ler_campo=`
  - l2scanner/renda_console.py::linhas_do_piso_em_uso + os tres fatos da varredura no resumo
affects:
  - o fim da Fase 3 (o LEIT-10 era o requisito que o ROADMAP nao tinha listado)

tech-stack:
  added: []          # NENHUMA dependencia nova. `requirements.txt` intocado.
  patterns:
    - "decisao no modulo PURO, custo na casca: `pisos_vizinhos` devolve a ordem, o laco paga o OCR"
    - "constante DERIVADA carrega a derivacao ao lado (a conta, o alvo e a hipotese pelo nome)"
    - "carencia MULTIPLICATIVA em vez de fixa, porque um numero que converge nao precisa que ninguem acerte o teto"
    - "portao de arvore de sintaxe olhando DENTRO da chamada, para a prosa atravessar"
    - "tabela declarada em MappingProxyType, para o portao de ausencia de memoria continuar valendo"

key-files:
  created:
    - l2scanner/renda_pisos.py
    - tests/test_renda_pisos.py
    - tests/test_renda_leit10.py
  modified:
    - l2scanner/renda_leitura.py
    - l2scanner/renda_laco.py
    - l2scanner/renda_console.py

decisions:
  - "o alcance da varredura e 4 passos (o deslocamento MEDIDO do M-S) e nao a meia-banda gravada de 1 a 2 -- andar dentro da banda gravada nao teria salvo o caso real"
  - "`RECUSAS_SEGUIDAS_PARA_VARRER = 13` sai da aritmetica (`0,79^13 = 4,7%` contra o alvo de 5%) e nao do molde de 3 dos irmaos, que dispararia em 49% dos tiques"
  - "uma varredura PERDIDA zera a serie e dobra a exigencia (13/26/52, teto 4x); sem isso o modo morre de estouro de orcamento num campo que recusa 79% por natureza"
  - "o piso lembrado e esquecido no GATILHO seguinte e nao na recusa avulsa: com 79% de recusa, esquecer na primeira nao deixaria a memoria sobreviver a um tique"
  - "o laco le campo a campo APENAS quando ha memoria de piso; a escolha nao e de orcamento (as duas formas empatam no ruido) e sim de contrato"
  - "perder em TODOS os pisos vira uma mensagem que diz que o suspeito e o RETANGULO e manda ao `calibrar-renda.bat` (M-Y)"
  - "nada volta ao `calibration.json`, com portao de AST cobrindo os quatro caminhos"

metrics:
  duration: "~3h"
  completed: 2026-09-03

actuals:
  tokens: 26320      # chars/4 sobre as 2.348 linhas adicionadas (105.281 chars)
  tasks: 3
  commits: 6
---

# Phase 3 Plan 03: O LEIT-10, a varredura de pisos vizinhos — Summary

**Antes de declarar que um campo parou de sair, o laço anda pelos pisos vizinhos e usa
o primeiro que produzir leitura válida — e diz na tela qual usou.** O alcance é o
deslocamento **medido** (4 passos), não a banda gravada; o gatilho é uma corrida de 13
recusas, que é a aritmética e não o molde; e uma varredura perdida **dobra a própria
carência** em vez de se repetir para sempre — sem o que o requisito não caberia no
orçamento de um tique de 1 Hz.

## O que foi construído

| Peça | Arquivo | O que faz |
|---|---|---|
| `ler_um_campo(...)` | `renda_leitura.py` | A porta de UM campo com UM piso. `ler_os_tres_campos` passa a **delegar** a ela. |
| `SUBCHAVE_POR_CAMPO` | `renda_leitura.py` | A tabela declarada campo → sub-chave, pública porque o laço precisa achar o piso gravado. |
| `pisos_vizinhos(...)` | `renda_pisos.py` (178 linhas) | O planejador **puro**: recebe inteiros, devolve inteiros, na ordem. |
| a varredura | `renda_laco.py` | Entre a leitura e a classificação de estado — literalmente o "antes de declarar". |
| `linhas_do_piso_em_uso(...)` | `renda_console.py` | A seção do bloco por intervalo, que **só aparece** quando alguém saiu do gravado. |
| os três fatos | `renda_console.py` | Quantas varreduras rodaram, quantas venceram, em que desvio o campo ficou. |

### A ordem do tique, depois desta fase

1. lê os três campos — no piso **gravado**, ou no **lembrado** de cada campo se houver;
2. colhe os quatro sinais crus **uma vez** (eles servem a duas perguntas);
3. se o frame mostra o jogo, roda a **varredura** dos campos que estão em corrida de recusa;
4. `classificar_a_visao` recebe os campos **depois** da varredura;
5. grava, imprime a linha, e o bloco por intervalo mostra o piso em uso.

## Números medidos, e três deles derrubaram uma frase

### 1. `BASE_RENDA` não é 710 — é **880** neste worktree

O plano gravou `BASE_RENDA = 710`, medido no checkout principal antes das ondas 1 e 2
serem fundidas. **Remedido aqui, no commit base, antes de tocar em `renda_leitura.py`:**

    PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest -k renda -q
    -> 880 passed, 5243 deselected, em 37,0 s

A diferença são os testes que o `03-02` e o `03-04` acrescentaram. **O número de
planejamento não vence o número medido no momento da execução**, e a comparação final
é a que o plano exigiu — **igualdade, e nunca `>=`**:

| | |
|---|---|
| base medida aqui | **880** |
| testes novos (`test_renda_leit10.py` 48 + `test_renda_pisos.py` 23) | **71** |
| `-k renda` no fim | **951 passed, 0 failed** |
| `880 + 71` | **951** ✅ |

A igualdade é o que responde à pergunta que a comparação existe para responder: um
`passed` que subisse **menos** que 71 significaria que a extração de `_ler` apagou um
teste que rodava, e um `>=` esconderia exatamente esse caso.

### 2. A afirmação de que "o desempacotamento por campo triplicaria o custo" **não se sustenta**

O plano justificava passar os moldes adiante dizendo que desempacotá-los por campo
triplicaria o custo do caminho de produção. **Medido, com a função de produção, contra
a fixtura de campo (11 moldes gravados):**

| | |
|---|---|
| `glifos_de_calibracao` (o desempacotamento) | **0,017 ms** |
| uma leitura completa de adena | **5,3 ms** |

Três milésimos. `ler_os_tres_campos` continua desempacotando uma vez e passando adiante
— **mas a razão é higiene, e não orçamento**, e isso está escrito na docstring com o
número. Um argumento de custo que não tem custo atrás vira folclore na próxima fase.

E a medição que decide de verdade é outra: **as duas formas de ler os três campos
empatam dentro do ruído.** Intercaladas, 40 rodadas de cada:

    ler_os_tres_campos   mediana 36,1 ms   (min 16, max 118)
    3x ler_um_campo      mediana 32,0 ms   (min 17, max 135)

O OCR domina e varia por um fator de sete. É por isso que o laço pode ler campo a campo
quando há piso lembrado **sem pagar nada por isso** — e por isso a escolha de manter
`ler_campos` como porta padrão é de contrato, e não de orçamento.

### 3. O custo do pior caso da varredura, medido com a função de produção

Chamando `renda_laco._varrer_os_vizinhos` + `renda_leitura.ler_um_campo` — o mesmo par
que roda no tique — contra `montagem_completa.png`. Mediana de 15 rodadas:

| campo | pior caso (8 tentativas, todas perdidas) | melhor (vence na 1ª) |
|---|---|---|
| nível | **27,9 ms** | 6,2 ms |
| EXP | **95,4 ms** | 15,2 ms |
| adena | **0,6 ms** | 5,7 ms |

Duas coisas que esta medição ensinou, e nenhuma era o que se esperava:

- **O pior caso cabe no tique de 1 s.** 95 ms é o teto, no campo mais caro. O risco de
  orçamento **não é uma varredura** — é a varredura **repetida em todo tique**, que é
  exatamente o que a carência existe para impedir. Com ~79% de recusa e sem carência,
  95 ms viram ~75 ms de imposto por tique, para sempre.
- **A varredura perdida da adena é a mais barata das três** (0,6 ms contra 5,7 ms da
  vencedora), porque o caminho de glifo desiste na máscara vazia antes de segmentar.
  Perder rápido sai de graça do desenho da Fase 1.

*Como o pior caso foi forçado, e por que isso é honesto:* contra a calibração real a
varredura **vence na primeira tentativa nos três campos** (a banda é larga). Para medir
as oito perdas usou-se a mesma função de produção com uma `entrada` cujo piso gravado
está fora da banda (60) — que é literalmente o caso do M-Y.

### 4. Importar `calibrar_renda` arrasta **353 módulos** e **~1,0 s**

Por isso `PASSO_DA_GRADE` é **copiado** e não importado, com teste afirmando que os dois
valores concordam (o precedente é `mercado_registro.py:65`). A suíte paga o import do
calibrador uma vez para que a produção não pague. `cv2`, `numpy` e `argparse` entram
todos.

## O que caiu durante a execução, e fica escrito

### O portão de import passava por duas das seis formas de arrastar o `cv2`

A primeira versão de `importados_por` guardava só o **primeiro** segmento do caminho
pontuado e o caminho inteiro. Com isso `import l2scanner.calibracao` virava
`{"l2scanner", "l2scanner.calibracao"}` — **sem `calibracao` em lugar nenhum** — e
passava direto. Dois dos seis controles positivos ficaram vermelhos na primeira rodada e
derrubaram a função, que passou a devolver **todos** os segmentos.

É o mesmo defeito que o `<done>` da Tarefa 2 já nomeava no `grep` que ele removeu — e
ele reapareceu na substituição. **Um portão que só o autor testa é um portão que só o
autor acredita.**

### Uma mutação sobreviveu, e ela obrigou um teste novo

`test_O_PISO_LEMBRADO_E_ESQUECIDO_E_A_SERIE_RECOMECA_DO_GRAVADO` **não prova o
esquecimento.** Apagar as duas linhas que esquecem o piso deixou os 47 testes **verdes**,
porque `_varrer_os_vizinhos` recebe o piso gravado por construção e a ordem da varredura
não depende da memória.

O que o esquecimento muda de verdade é a **leitura do tique seguinte**: sem ele o campo
continuaria sendo lido no piso lembrado pelo resto da noite — uma calibração paralela e
invisível. O sintoma seria cruel: o usuário recalibraria, o piso gravado passaria a estar
certo, e o laço continuaria lendo no piso velho até o processo ser reiniciado.
`test_DEPOIS_DE_UMA_VARREDURA_PERDIDA_O_TIQUE_VOLTA_AO_PISO_GRAVADO` existe por causa
disso, e a docstring do teste que falhou **carrega a história em vez de a apagar**.

### A guarda de sub-chave ausente é inalcançável pelo disco

Gravar uma entrada sem `nivel` num arquivo e carregá-la **não** chega àquela recusa:
`calibracao.py:1495-1505` levanta `CalibracaoInvalida` no próprio carregamento, com a
frase *"uma entrada pela metade é pior que uma entrada ausente"*. O esquema já fecha o
caminho do disco; a guarda de `ler_um_campo` cobre o que sobra — um objeto `Calibracao`
alterado em memória. O teste mutila em memória e **diz por quê**: escrever o arquivo
mediria a validação do esquema e chamaria isso de leitura.

## A incerteza A3, declarada no fonte (e não só no plano)

Toda a aritmética de `RECUSAS_SEGUIDAS_PARA_VARRER` assume que as recusas do nível são
**independentes tique a tique**, e **ninguém mediu isso**. Os 79% são uma *taxa* sobre
**14 amostras**, e a distribuição de comprimento das corridas não existe em documento
nenhum deste workstream. Há razão física para suspeitar que elas são **correlacionadas**:
a recusa vem do cenário atrás da barra semitransparente, e cenário muda em segundos, não
em frames.

Se as recusas forem clusterizadas, **o K certo é maior que 13** — e a carência
multiplicativa é o que torna esse erro **barato**: mesmo com o K subestimado, a segunda
varredura perdida já exige uma corrida de 26 e a terceira uma de 52. O que mede isto,
quando alguém quiser: o CSV de `.renda/` já grava **uma linha por tique** com o motivo
por campo, e uma noite de farm dá a distribuição de graça, sem instrumentação nova.
Quando ela existir, muda-se **um** número.

## O M-Y: o modo de falha irmão, e o que esta fase faz a respeito

O `03-ACHADO-DO-LEVEL-UP.md` mediu, no mesmo dia, o caso que a varredura **não** conserta:
o painel de status moveu ~90 px e o retângulo do nível passou a apontar para **grama
pura**. Nenhum piso, em nenhum alcance, lê um número em grama.

| o que mudou | como se vê | conserto |
|---|---|---|
| brilho do fundo | o campo sai num piso vizinho | **varredura** (LEIT-10) |
| posição do painel | o campo não sai em piso NENHUM | **`calibrar-renda.bat`** |

Os dois se manifestam idênticos de fora e pedem consertos **opostos**. Perder em **todos**
os pisos do alcance é a única hora em que o produto pode dizer *"o retângulo, e não o
brilho"* **com prova na mão** — e é o que a mensagem da varredura perdida diz, mandando o
usuário ao calibrador e avisando que ela não vai se repetir a cada tique.

**Isso não duplica o `03-02`.** Aquele plano já escreve a mesma suspeita no bloco alto de
`SEM LEITURA`, e ela continua lá inteira — mas é uma **suspeita** ("se isto persistir, o
suspeito é o retângulo"). A desta fase é uma **observação**: a varredura rodou, tentou os
oito pisos e perdeu os oito. O estado continua sendo `SEM LEITURA` e nunca `PAUSADO`,
exatamente como o `03-02` construiu.

## Verificação

| # | Verificação do plano | Resultado |
|---|---|---|
| 1 | Suíte fecha em **>= 5778 passed**, mesmas 15 falhas, nenhuma nova | ✅ **15 failed, 6010 passed, 24 skipped**. As 15 são as bombas-relógio de `date.today()` em `test_sessao.py` / `test_janela_no_relogio.py` / `test_respawn.py`. Zero falhas novas. |
| 2 | `tests/test_renda_par.py` verde com `renda_pisos.py` e a varredura na árvore (LEIT-11) | ✅ Verde. O laço chama `renda_conta` e nunca as regras de par; o portão do chamador único não enxerga nem `renda_pisos.py` nem a varredura. |
| 3 | Teste de AST afirmando que `renda_laco.py` não escreve calibração, **com controle positivo** | ✅ `escritas_de_calibracao` cobre os quatro caminhos (`cal.salvar()`, `getattr(cal,"salvar")()`, `salvar(cal)` importado, literal `calibration.json` **dentro de uma chamada**), e os quatro controles positivos são acusados. Olha dentro da chamada para a prosa atravessar — a lição medida do `03-02`, em que um portão textual devolveu 9 linhas para 1 chamada. |
| 4 | Um teste mede a linha do tique no pior caso e afirma `<= 76` colunas | ✅ Com a varredura ativa e o piso movido: `<= 76`, **sem `~`** e **sem a palavra `piso`**. O marcador sai no bloco por intervalo e numa linha de log com latch. |
| 5 | O custo medido de uma varredura completa está escrito num comentário do fonte | ✅ Pior e melhor caso dos três campos, medidos com a função de produção. Ver "Números medidos" nº 3. |

### Critérios de sucesso

- ✅ Antes de declarar que um campo parou de sair, o laço tenta os vizinhos e usa o
  primeiro que produzir leitura válida — a varredura roda **entre** a leitura e
  `classificar_a_visao`.
- ✅ O alcance é de 4 passos, o deslocamento **medido**, e não a meia-banda gravada de 1
  a 2. Há teste afirmando que `170` (o centro da banda nova do M-S) está na sequência de
  fábrica e **não** está na de meia-banda — a refutação executável de "use a largura do
  arquivo".
- ✅ O piso que funcionou aparece na tela e no log e **não** volta para o
  `calibration.json`.
- ✅ A varredura custa **uma leitura de campo por tentativa**, dispara só numa corrida de
  recusas, e o regime estável volta a uma leitura por campo.
- ✅ `renda_leitura.py` continua puro e sem memória (o portão de ausência de memória segue
  verde) e **nenhuma leitura de fixtura mudou de resultado** — 951 contra 880 + 71.

### Portões com mutação E controle

| Mutação aplicada à produção | Resultado |
|---|---|
| a varredura perdida **não** zera a série | 🔴 2 testes |
| a carência **não** dobra (multiplicador fixo em 1) | 🔴 2 testes |
| a carência **não** tem teto | 🔴 1 teste |
| o gatilho ignora o multiplicador (`>= K` puro) | 🔴 1..2 testes |
| o piso lembrado **não** é esquecido no gatilho | 🔴 1 teste *(sobreviveu na 1ª rodada — ver acima)* |
| a leitura válida **não** devolve o multiplicador a 1 | 🔴 1 teste |
| `ALCANCE_EM_PASSOS` 4 → 2 (a meia-banda gravada) | 🔴 8 testes |
| a ordem do sinal invertida (`-5, +5` em vez de `+5, -5`) | 🔴 3 testes |
| **CONTROLE** — `if x < y` reescrito como `if not x >= y` | 🟢 48 passed |
| **CONTROLE** — o corpo de `pisos_vizinhos` reescrito com compreensão | 🟢 23 passed |

## Higiene

- **Nenhuma dependência nova.** `requirements.txt` intocado. `rich` continua fora.
- **Nenhum arquivo do `dashboard` tocado**, nenhum `.bat`, nenhum `ROADMAP.md`, nenhum
  `STATE.md`. Seis arquivos: `renda_leitura.py`, `renda_pisos.py`, `renda_laco.py`,
  `renda_console.py` e os dois de teste.
- **Nenhuma deleção de arquivo** em nenhum dos seis commits.
- Nenhum stub, nenhum `TODO`/`FIXME` novo, nenhum teste pulado acrescentado. Os 24 skips
  da suíte são os de ambiente (bindings de OCR no Python global), inalterados.
- **A medição foi feita só com código de produção**: os três cronômetros chamam
  `renda_laco._varrer_os_vizinhos`, `renda_leitura.ler_um_campo` e
  `renda_leitura.ler_os_tres_campos`. Nada foi reimplementado "só para conferir".

## Self-Check: PASSED
