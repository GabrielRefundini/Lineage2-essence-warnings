---
phase: 03-o-modo-renda-o-painel-ao-vivo-e-a-cegueira-declarada
plan: 01
subsystem: renda
tags: [laco, console, cli, tracer, CONS-01, CONS-02, LEIT-11]
status: complete

requires:
  - renda_leitura.ler_os_tres_campos (Fase 1)
  - renda_conta.passo_entre_campos / contar_o_passo / as_duas_taxas / tempo_ate_o_nivel (Fase 2)
  - renda_registro.RegistroDaRenda (Fase 2)
  - captura_janela.JanelaSource, frames.SaudeDoFrame, relogio.Relogio
  - mercado_console.OrcamentoDoTick, LARGURA_DO_AVISO; console.moldurar
provides:
  - l2scanner/renda_laco.py::laco_da_renda  # contrato das ondas 2 e 3
  - l2scanner/renda_console.py::linha_do_tique / bloco_da_renda / resumo_da_sessao_da_renda
  - l2scanner/__main__.py::montar_registro_da_renda
  - a flag --renda, o portao da mira e o despacho
affects:
  - 03-02 (cegueira: usa a fonte com capturar() e o parametro estado=)
  - 03-03 (LEIT-10: o retry de piso mora neste laco)
  - 03-04 (vigiar-renda.bat: depende do resumo sair do proprio programa)

tech-stack:
  added: []          # NENHUMA dependencia nova. `rich` continua fora.
  patterns:
    - "casca fina + modulo puro: o laco decide nada, o console devolve texto"
    - "cinco alavancas de injecao por parametro nomeado, producao passa zero"
    - "portao de arvore de sintaxe COM controle positivo"

key-files:
  created:
    - l2scanner/renda_laco.py
    - l2scanner/renda_console.py
    - tests/test_renda_laco.py
    - tests/test_renda_console.py
    - tests/test_renda_no_main.py
  modified:
    - l2scanner/__main__.py
    - l2scanner/renda_modo.py

decisions:
  - "a linha do tique NAO carrega `n`: ela ja mede 58 colunas limpa e o teto medido e 72"
  - "a fonte das recusas POR CAMPO e o laco, e nao `contagem.recusadas_por_motivo` (achado que derruba o plano)"
  - "as tres grafias mudaram de `renda_modo` para `renda_console` por medicao de custo de import"
  - "o bloco sai na PRIMEIRA volta e nao antes do primeiro tique: nao ha `CamposDaRenda` no arranque"

metrics:
  duration: "~2h"
  completed: 2026-09-03

actuals:
  tokens: 32515      # chars/4 sobre as 3.362 linhas adicionadas
  tasks: 3
  commits: 3
---

# Phase 3 Plan 01: A fatia do `--renda` — Summary

O laço de produção do modo `--renda`: captura por janela com `capturar()`, leitura da Fase 1,
conta da Fase 2, uma linha por tique em `.renda/<apelido>.csv`, uma linha de log por tique que
**rola** e um bloco por intervalo com as quatro taxas, o ETA e os dois tempos da sessão.

**`.renda/` deixou de estar vazio** — que era o produto desta fase do ponto de vista do usuário.

## O que foi construído

| Peça | Arquivo | O que faz |
|---|---|---|
| `laco_da_renda(args, cal, *, fonte, ler_campos, relogio, pasta, ticks_maximos)` | `renda_laco.py` (648 linhas) | O chamador que faltava. Devolve código de saída e nunca levanta. |
| `linha_do_tique(campos, contagem, *, estado=None)` | `renda_console.py` | Uma linha por tique, 58–72 colunas medidas. |
| `bloco_da_renda(...)` | `renda_console.py` | O bloco por intervalo, ≤69 colunas medidas contra o teto de 76. |
| `resumo_da_sessao_da_renda(...)` | `renda_console.py` | O `finally`, e ele sai **sempre**. |
| `montar_registro_da_renda(pasta, personagem)` | `__main__.py` | Devolve `None` e nunca levanta nos três modos de falha. |
| `--renda`, o portão da mira, o despacho | `__main__.py` | A quarta invocação, ao lado do `--mercado`. |

### As três decisões que a medição tomou

**1. A largura da linha do tique, medida em caracteres e não afirmada.**

| Linha | Colunas |
|---|---|
| `renda \| nivel 67 \| EXP 79,2568% \| adena 17.592.060 \| LENDO` | **58** |
| `renda \| nivel -- \| EXP 79,2568% \| adena 17.592.060 \| nivel: campo-vazio` | **71** |
| `renda \| nivel -- \| EXP -- \| adena -- \| nivel, EXP, adena: campo-vazio` | **69** |
| pior caso, motivo mais longo da Fase 1 truncado com `~` | **72** |

Todas dentro da banda 58–72 do plano, e todas abaixo das 76 de `LARGURA_DO_AVISO`. O teste
percorre as **oito** combinações de recusa — a recusa é o caso majoritário (79% no nível), não a
exceção.

**2. As três grafias mudaram de `renda_modo` para `renda_console`, e a razão é um número.**
Medido no mesmo processo: `import l2scanner.renda_modo` custa **0,974 s e 344 módulos, com `cv2`
carregado** (aquele módulo é a ferramenta de linha de comando e importa `argparse` e `cv2` no
topo); `renda_conta` + `console` custam **0,198 s e 279 módulos**. O laço da noite inteira não
paga um `cv2` para escrever `17.592.060`. `renda_modo.py` passou a importar daqui — uma verdade,
numa casa só, porque o critério 1 da Fase 1 é uma **comparação** entre o terminal e o monitor.

**3. O bloco sai na PRIMEIRA volta, e não antes do primeiro tique.** O plano pedia "uma vez no
arranque, antes do primeiro tique". Isso é impossível aqui e a razão é estrutural:
`bloco_da_renda` precisa de `CamposDaRenda`, e no arranque nada foi lido ainda. O irmão do
mercado consegue porque `desenhar_a_analise` lê o **disco**, e a renda não tem análise de
histórico nesta fase. O efeito prático que o plano queria — "o usuário não espera trinta segundos
sem saber se o cálculo está vivo" — está preservado: `proximo_bloco` nasce no `monotonic()` de
agora, então o tique 1 já o dispara. O teste afirma **uma** saída em dez tiques, com o controle
de que com `--status-a-cada 0` ele sai nas três.

## Números que caíram, e eles dizem que caíram

### 1. A fonte das taxas de recusa POR CAMPO não é `contagem.recusadas_por_motivo`

O plano manda, com todas as letras: *"A fonte dos números é `contagem.recusadas_por_motivo` sobre
o total de tiques"*. **Isso é falso, e o fonte prova.** `contar_o_passo` alimenta aquele
dicionário a partir de `passo.recusas`, e a docstring de `PassoDaRenda` (`renda_conta.py:342-347`)
diz o que ela é: *"a TUPLA QUE `conferir_o_par` DEVOLVEU, inteira"* — recusas de **par** —, e
segue: *"Ela também sai vazia no caminho de `CamposDaRenda` com um campo recusado"*.

Ou seja: os **79% do nível, 21% da adena e 0% do EXP** medidos na Fase 1 não passam por aquele
dicionário em tique nenhum. Um bloco montado como o plano mandava mostraria três zeros para
sempre — e o requisito existe exatamente porque *"um painel que as esconde faz o usuário concluir
que o scanner travou"*.

**Conserto:** o laço conta as recusas por campo a partir de `CamposDaRenda.por_campo`, todo tique
(não só nos aceitos), e passa o contador ao console. Há teste de laço que roda quatro tiques com
o nível recusado e afirma `nivel 100%` / `EXP 0%` no bloco — ele fica vermelho se o laço parar de
contar.

### 2. As duas seções de recusa do resumo tinham o MESMO título

Por uma revisão deste trabalho, `resumo_da_sessao_da_renda` e `bloco_da_renda` abriam a seção com
`POR QUE O \`n\` E ESSE` — e as duas mostram **fatos diferentes**: recusa por campo (o pixel não
virou número; conserto = calibrar o retângulo) e recusa de par (a guarda pegou um número
incrível; conserto = desconfiar da leitura). O defeito apareceu na hora: um teste que procurava
um número pelo título achava o outro. Agora são `RECUSA POR CAMPO` e `RECUSA DE PAR`, com a
diferença escrita, e há teste afirmando que os dois títulos não colidem.

### 3. A verificação nº 4 do plano (`grep -c capturar_completo <= 1`) é fraca e foi substituída

**Medido:** `grep -c capturar_completo l2scanner/renda_laco.py` devolve **5**. Quatro dessas
linhas são a **docstring que explica a C-5** — por que `capturar_completo` não pode aparecer no
corpo do tique e por que a cegueira do `03-02` morre se aparecer. A quinta é a chamada real.
O portão de árvore de sintaxe conta **CHAMADAS** e devolve **1**.

Enfraquecer a documentação para satisfazer um `grep` que não distingue docstring de chamada seria
o inverso do que o próprio plano decidiu quando **removeu** o `grep` de `rich` do `<verify>`:
*"um portão fraco ao lado de um forte ensina que o fraco basta"*. O portão de AST tem controle
positivo (um módulo falso com a chamada é acusado) e um segundo portão que varre **só o corpo do
`while`** — esse é o que mede a intenção real da verificação.

### 4. O piso da suíte é 5754 neste worktree, e 5778 no checkout principal

**Medido no worktree, no commit base, com a árvore limpa:** `15 failed, 5754 passed, 24 skipped,
145 deselected`. O prompt e o plano dão **5778 passed** — a diferença é **exatamente os 24
skipped**, e a causa é a mesma armadilha que derrubou a P-1: `calibration.json` é gitignored e
**não existe dentro de um worktree**, então 24 testes que rodam no checkout principal aqui pulam
com skip nomeado.

Comparar contra 5778 daqui teria dado um falso "faltam 24" a cada rodada. **O piso desta execução
é 5754**, medido onde ela roda, e ele é `passed` e nunca `passed + skipped`.

## Verificação

| # | Verificação do plano | Resultado |
|---|---|---|
| 1 | Suíte `>=` piso, mesmas 15 falhas, nenhuma nova | **15 failed, 5838 passed** (+84 sobre o piso de 5754 deste worktree). Zero falhas fora das 15 bombas-relógio de `date.today()`. |
| 2 | `tests/test_renda_par.py` continua verde | ✅ 53 testes verdes com `renda_laco.py` na árvore |
| 3 | `grep -rn "import rich\|from rich" l2scanner/` = 0 | ✅ **0** |
| 4 | `grep -c capturar_completo` <= 1 | ❌ devolve **5** (4 são docstring). **Substituída** pelo portão de AST: **1 chamada**, e ela está no arranque. Ver "Números que caíram" nº 3. |
| 5 | `python -m l2scanner --renda` recusa sem traceback | ✅ `--renda exige --janela: a EXP e a adena sao do PERSONAGEM...` |
| 6 | Nenhum arquivo de `dashboard` nem `requirements.txt` | ✅ 7 arquivos tocados, nenhum deles |

### Critérios de sucesso

- ✅ `.renda/` nasce com **dois** arquivos: o CSV e o `LEIAME.txt` (C-10) — teste conta dois.
- ✅ Teste de laço roda **sem jogo aberto e sem OCR**, pelas cinco alavancas.
- ✅ Linha do tique sai todo tique, mede 58–72 colunas, mostra os três valores.
- ✅ Bloco com as quatro taxas (`n` + recência colados), ETA, os dois tempos da sessão, tempo em
  lacuna e as três taxas de recusa medidas.
- ✅ `--renda` existe, exige `--janela` pela razão certa, despacha ao lado do `--mercado`.
- ✅ `montar_registro_da_renda` devolve `None` e nunca levanta nos três modos de falha.
- ✅ Nenhuma dependência nova, nenhuma chave nova de config, nenhum arquivo do `dashboard`.

### Portões com mutação E controle

Nenhum critério afirma existência; todos medem. Cada portão foi quebrado de propósito e voltou:

| Mutação aplicada à produção | Resultado |
|---|---|
| o tique passa a usar `capturar_completo()` | 🔴 2 testes |
| o laço deixa de chamar `registrar` | 🔴 5 testes |
| a linha do tique ganha `n=` colado | 🔴 2 casos de largura |
| o portão da mira do `--renda` some | 🔴 2 testes |
| o despacho sobe para antes do `--janela AUTO` | 🔴 1 teste |
| só a taxa da sessão é mostrada | 🔴 3 testes |
| a sessão mostra só o tempo farmado | 🔴 2 testes |
| a taxa ausente vira `0` em vez do motivo | 🔴 2 testes |
| a recusa rara é arredondada para zero | 🔴 1 teste |
| o bloco volta a sair por tique | 🔴 1 teste |

| Controle (refatorar mantendo a saída) | Resultado |
|---|---|
| `estado_da_leitura` reescrita com laço em vez de compreensão | 🟢 48 verdes |
| `_grafia_curta` reescrita sem `divmod` | 🟢 70 verdes |

## Desvios do plano

### Auto-corrigidos

**1. [Regra 3 — bloqueio] `montar_registro_da_renda` foi adiantada da Tarefa 2 para a Tarefa 1.**
- **Achado durante:** Tarefa 1. `laco_da_renda` chama `principal.montar_registro_da_renda`, e a
  fatia não fecha ponta a ponta sem ela — o próprio `<read_first>` do plano diz *"o `hasattr` da
  renda pergunta por `montar_registro_da_renda`, que a Tarefa 2 cria"*.
- **Conserto:** a função entrou no commit da Tarefa 1; a Tarefa 2 trouxe a flag, o portão, o
  despacho e **os testes dela**.
- **Commit:** `7c882ac` (função), `6bd647a` (testes).

**2. [Regra 2 — correção] As recusas por campo passaram a ser contadas pelo laço.**
Ver "Números que caíram" nº 1. Sem isso o requisito de CONS-01 mostraria três zeros para sempre.
- **Commit:** `c951e13`.

**3. [Regra 1 — defeito] Os dois títulos colididos do resumo.**
Ver "Números que caíram" nº 2. Encontrado por um teste que procurava o número errado.
- **Commit:** `c951e13`.

### Assinaturas que divergem do esboço do plano, e por quê

- `bloco_da_renda(..., recusas_por_campo, tiques)` — o esboço não tinha os dois, porque assumia a
  fonte errada para o número (item 1 acima). Sem eles o bloco não tem como cumprir CONS-01.
- `resumo_da_sessao_da_renda(contagem, orcamento, registro, *, recusas_por_campo, tiques)` — o
  esboço pedia `desde`/`ate`; a duração da sessão vive no **bloco** (que tem os dois tempos) e o
  resumo ganhou no lugar as taxas de recusa por campo, que é o número que o usuário lê quando a
  janela do `.bat` está fechando. Os parâmetros são **obrigatórios** de propósito: um default
  faria a seção sumir em silêncio.
- `resumo_da_sessao_da_renda` nasceu na Tarefa 1 (o `<behavior>` dela exige o resumo no `finally`)
  e a Tarefa 3 o expandiu, em vez de criá-lo do zero.

### Escolha de desenho registrada com a alternativa

**A linha do tique carrega o motivo da recusa no ESTADO e não no slot do campo.** Medido: com o
motivo inline em cada campo, dois campos recusados dão 76 colunas e três dão mais — acima do teto
de 72. Com o motivo agrupado no estado (`nivel, EXP: campo-vazio`), as oito combinações cabem.
*Alternativa registrada:* abreviar o motivo dentro do slot de cada campo. Custaria uma abreviação
por campo e ainda estouraria com três recusas — que é o caso que a Fase 1 mediu como frequente.

## Contratos para as ondas 2 e 3

- `laco_da_renda(args, cal, *, fonte=None, ler_campos=None, relogio=None, pasta=None, ticks_maximos=None) -> int`
- `linha_do_tique(campos, contagem, *, estado=None) -> str` — **`estado=` já existe e ainda não faz
  nada**: é por onde o `03-02` injeta `PAUSADO: JOGO CAIU` e `PARADO ha 4min12` sem tocar na
  assinatura. Há teste afirmando que o estado injetado substitui o calculado.
- A fonte de produção é `JanelaSource` com `capturar()` — `SaudeDoFrame` chega ao laço em
  `frame.saude` e ainda **não é consultada**; é o que torna CEGO-01/02 possíveis no `03-02`.
- `recusas_por_campo` e `desde` são estado do laço, fora do `while`, prontos para o `03-03`
  acrescentar o piso usado.

## Known Stubs

| Local | O que é | Por que é intencional | Quem resolve |
|---|---|---|---|
| `renda_console.linha_do_tique`, parâmetro `estado=None` | aceito e documentado como "ainda não faz nada em produção" | precedente literal das cinco chaves que o `02-01` deixou lidas e sem consumidor; existe agora para o `03-02` não mexer na assinatura | `03-02` |
| `renda_laco`, `frame.saude` não é lido | o laço captura com `capturar()` e não classifica | a classificação é CEGO-01/02 e é do `03-02`; construí-la aqui seria a fase seguinte antecipada sem os requisitos dela | `03-02` |

Nenhum dos dois impede o objetivo deste plano: `.renda/` deixou de estar vazio e o painel mostra
as quatro taxas, que é o que CONS-01 e CONS-02 pedem.

## Threat Flags

Nenhuma superfície nova fora do `<threat_model>` do plano. `T-03-09` (carimbo de geometria velho)
ficou **mitigada e viva**: a geometria vem de `frame.shape` da janela viva e a gravada virou
guarda, com aviso alto quando discordam. A calibração de fixtura versionada confirma a P-1
corrigida — `{'largura': 1720, 'altura': 1392}` nos **dois** personagens —, e essa evidência é
melhor que a do `calibration.json` porque está **dentro do repositório** e não some num worktree.

## Self-Check: PASSED

Arquivos criados, conferidos no disco:
- `l2scanner/renda_laco.py` — FOUND (648 linhas)
- `l2scanner/renda_console.py` — FOUND (660 linhas)
- `tests/test_renda_laco.py` — FOUND (916 linhas)
- `tests/test_renda_console.py` — FOUND (662 linhas)
- `tests/test_renda_no_main.py` — FOUND (356 linhas)

Commits, conferidos em `git log`:
- `7c882ac` — FOUND
- `6bd647a` — FOUND
- `c951e13` — FOUND
