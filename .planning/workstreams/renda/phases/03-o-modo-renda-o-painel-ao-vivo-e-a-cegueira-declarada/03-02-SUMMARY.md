---
phase: 03-o-modo-renda-o-painel-ao-vivo-e-a-cegueira-declarada
plan: 02
subsystem: renda
tags: [cegueira, staleness, painel, CEGO-01, CEGO-02, CONS-01]
status: complete

requires:
  - frames.SaudeDoFrame / FRAMES_IDENTICOS_PARA_CONGELADO (v1)
  - cliente.EstadoDoCliente / esta_na_tela_de_login / VigiaDoCliente (v1)
  - captura_janela.esta_minimizada / JanelaSource.estado_do_cliente (v1)
  - recaptura.FonteRecuperavel (v1, o incidente dos 33 minutos)
  - renda_conta.passo_entre_campos + DESCONTINUIDADE_DA_LACUNA (Fase 2)
  - renda_laco.laco_da_renda / renda_console.linha_do_tique(estado=) (03-01)
provides:
  - l2scanner/renda_estado.py::classificar_a_visao / RastreioDoValor / EstadoDaRenda
  - l2scanner/renda_console.py::aviso_da_transicao / duracao_curta (publica)
  - l2scanner/captura_janela.py::JanelaSource.hwnd
  - o laco pausando a gravacao, religando a fonte e contando os quatro estados
affects:
  - 03-03 (LEIT-10: a varredura de piso entra ANTES de `SEM LEITURA` virar veredito)

tech-stack:
  added: []          # NENHUMA dependencia nova. `rich` continua fora.
  patterns:
    - "casca colhe os sinais, modulo puro decide e nomeia"
    - "latch de transicao com marca distinta por estado, legivel sem cor"
    - "portao de arvore de sintaxe COM controle positivo, nunca `grep`"
    - "MappingProxyType em vez de dict nu, para o portao de memoria valer"

key-files:
  created:
    - l2scanner/renda_estado.py
    - tests/test_renda_estado.py
    - tests/test_renda_cegueira.py
  modified:
    - l2scanner/renda_laco.py
    - l2scanner/renda_console.py
    - l2scanner/captura_janela.py
    - tests/test_renda_console.py

decisions:
  - "a observacao do rastreio mora DENTRO de `classificar_a_visao`: um frame congelado devolve os mesmos numeros, e uma casca que observasse antes de perguntar sairia da cegueira anunciando PARADO"
  - "`VisaoDaRenda.texto` e `None` no caso LENDO, para a linha do tique continuar mostrando o motivo da recusa nos 79% de tiques do nivel"
  - "dois textos por estado: o CURTO rola por tique (76 colunas) e o ALTO sai uma vez por transicao (a frase acionavel tem ~240 caracteres)"
  - "o teto da linha do tique subiu de 72 para 76 por medicao: com 72, os CINCO estados novos saiam truncados"
  - "a transicao usa `console.moldurar` com marca por estado, e nao `destacar`: `destacar(tipo=None)` daria `*` para todos"

metrics:
  duration: "~3h"
  completed: 2026-09-03

actuals:
  tokens: 31380      # chars/4 sobre as 2.972 linhas adicionadas (125.521 chars)
  tasks: 3
  commits: 5
---

# Phase 3 Plan 02: A cegueira declarada e o "parado" — Summary

**"Não vejo" e "vejo e nada mudou" deixaram de ser a mesma palavra.** A cegueira
**suspende** a gravação e o parado **grava**; a tela diz qual dos cinco casos é, com
um texto acionável por motivo; e a série de staleness — a única peça genuinamente
nova da fase — mede o **EXP** e separa "mudou", "não mudou" e "não sei" em três fatos
que nunca se somam.

## O que foi construído

| Peça | Arquivo | O que faz |
|---|---|---|
| `classificar_a_visao(...)` | `renda_estado.py` (517 linhas) | Quatro sinais crus entram, um estado nomeado + texto acionável sai. |
| `RastreioDoValor.observar(...)` | `renda_estado.py` | A staleness de **valor**, que não existia na árvore. |
| `motivo_da_pausa(...)` | `renda_estado.py` | A metade barata: cego ou não, sem precisar de `CamposDaRenda`. |
| `aviso_da_transicao(visao)` | `renda_console.py` | O bloco alto, uma vez por mudança, com marca distinta por estado. |
| `JanelaSource.hwnd` | `captura_janela.py` | Duas linhas aditivas. O envelope a encaminha de graça. |
| `_a_janela_esta_minimizada` / `_o_estado_do_cliente` | `renda_laco.py` | A coleta dos dois sinais que não vêm no `Frame`. |
| `_montar_a_fonte(..., construir_janela=)` | `renda_laco.py` | A fábrica + `FonteRecuperavel`, com a **mira dentro da fábrica**. |

### Os cinco casos, e o disco concorda com a tela

| Estado | A tela diz | O disco |
|---|---|---|
| LENDO | `LENDO`, ou `nivel: campo-vazio` (o motivo do `03-01`, preservado) | grava |
| PARADO | `PARADO ha 4min n=250` | **grava** |
| SEM LEITURA | `SEM LEITURA (nivel, EXP, adena)` | grava, e o CSV carrega os três motivos |
| SEM LEITURA (EXP) | `SEM LEITURA (EXP)` | grava |
| PAUSADO | `PAUSADO: tela de login` | **não grava** |

## Números que caíram, e eles dizem que caíram

### 1. O teto de 72 colunas da linha do tique caiu — ele era do vocabulário ANTIGO

O `03-01` mediu `LARGURA_MAXIMA_DA_LINHA_DO_TIQUE = 72` como o teto da banda real. **O
número estava certo para DOIS estados** (`LENDO` e a lista de recusas). Esta fase traz
**cinco**, e os novos são mais longos. Medido com os valores lidos ao vivo em
2026-09-03 (`renda | nivel 68 | EXP 48,0075% | adena 23.986.985 | `, que custa 53
colunas), com o teto em 72:

```
 72  PARADO           ... | PARADO ha 4min n=2~      <- truncado
 72  PARADO longo     ... | PARADO ha 59min n=~      <- truncado
 72  PAUSADO login    ... | PAUSADO: tela de l~      <- truncado
 72  PAUSADO desconec ... | PAUSADO: desconect~      <- truncado
 72  PAUSADO preto    ... | PAUSADO: frame pre~      <- truncado
```

**Todos os estados novos perdiam o fim** — e o fim é a contagem de amostras que o
CEGO-02 pede pelo nome e o motivo da pausa que o CEGO-01 existe para dizer. Manter 72
teria sido preservar um número medido para outro conjunto de linhas.

**Conserto:** o teto passou a ser `LARGURA_DO_AVISO` (76) — que **não é escolha nova**:
é o único número de largura de console que este fonte cita com razão ao lado (*"a
largura em que ela cabe num console padrão de 80"*) e já era o teto do bloco por
intervalo do mesmo arquivo. Remedido com 76, **o pior caso é 75 e nada trunca**:

```
 75  PARADO longo     renda | nivel 68 | EXP 48,0075% | adena 23.986.985 | PARADO ha 59min n=3599
 75  PAUSADO login    renda | nivel 68 | EXP 48,0075% | adena 23.986.985 | PAUSADO: tela de login
 73  PARADO           renda | nivel 68 | EXP 48,0075% | adena 23.986.985 | PARADO ha 4min n=250
 70  SEM LEITURA (3)  renda | nivel -- | EXP -- | adena -- | SEM LEITURA (nivel, EXP, adena)
 64  SEM LEITURA(EXP) renda | nivel 68 | EXP -- | adena 23.986.985 | SEM LEITURA (EXP)
```

O teste de largura afirma as duas coisas: `<= 76` **e** `"~" not in linha`. A segunda é
a que importa — sem ela, o teste passaria com tudo truncado.

### 2. A verificação nº 3 do plano (`grep -rn "esta_minimizada"`) é fraca, pelo mesmo motivo do `03-01`

**Medido:** `grep -rn "esta_minimizada" l2scanner/` devolve **9 linhas** para **1**
chamada. Sete delas são a prosa que explica por que aquela função é consultada em vez
de se confiar no congelamento — inclusive a docstring da `@property hwnd` e o registro
da incerteza A2.

Enfraquecer a documentação para satisfazer um `grep` seria o inverso do que esta fase
decidiu ao **remover** o `grep` do `<verify>` da Tarefa 1. O portão real é de árvore de
sintaxe (`chamadores_de`), conta **chamadas**, devolve **exatamente 1** — em
`renda_laco.py` — e tem controle positivo (dois módulos falsos, um com `from ... import`
e outro com `modulo.funcao`, são acusados os dois).

### 3. `SEM LEITURA` não cabe com o motivo, e o motivo NÃO se perdeu

Medido: `SEM LEITURA (nivel, EXP, adena: campo-vazio)` custa **83 colunas** com o
prefixo, contra o teto de 76; e o caso do EXP, **79**. Os dois sairiam truncados
justamente no motivo.

**Decisão:** o texto da tela nomeia os **campos** e o motivo viaja em dois lugares onde
ele cabe inteiro — a **coluna própria de cada campo no CSV** (há teste afirmando
`motivo_do_nivel`, `motivo_do_exp` e `motivo_da_adena` iguais a `campo-vazio`) e o
**bloco alto da transição**, que sai uma vez e tem 76 colunas só para ele.

**E o caminho de 79% ficou intacto:** quando só o nível recusa e o EXP sobe, o estado é
LENDO e `visao.texto` é `None` — então `linha_do_tique` calcula o texto dela mesma e
continua imprimindo `nivel: campo-vazio`, exatamente como o `03-01` escreveu. Há teste
afirmando isso na fatia inteira.

### 4. O piso da suíte é 5853 neste worktree, e a execução fechou em 5922

**Medido aqui, neste worktree, no commit base, com a árvore limpa:**
`15 failed, 5853 passed, 24 skipped, 145 deselected`.

O prompt dá **5838** para o checkout principal; a diferença é de commits fundidos no
tronco entre as duas medições, e a lição do `03-01` continua valendo — o número de fora
não serve de piso aqui, porque `calibration.json` é gitignored e não existe dentro de um
worktree. **O piso desta execução é 5853, medido onde ela roda.**

## Verificação

| # | Verificação do plano | Resultado |
|---|---|---|
| 1 | Suíte `>= 5778 passed`, mesmas 15 falhas, nenhuma nova | **15 failed, 5922 passed, 24 skipped** (+69 sobre o piso de 5853 deste worktree). As 15 são as bombas-relógio de `date.today()` em `test_sessao.py` / `test_janela_no_relogio.py` / `test_respawn.py`. Zero falhas novas. |
| 2 | `test_recaptura.py` e o teste da janela continuam verdes | ✅ `test_recaptura.py` verde, inclusive o que prende que o envelope **encaminha** `estado_do_cliente` em vez de declarar. A `@property hwnd` é aditiva e há teste afirmando que o envelope **não** a declara. |
| 3 | `grep` mostra a definição e **um** chamador de produção | ❌ o `grep` devolve **9 linhas** (7 são prosa). **Substituída** pelo portão de AST: **1 chamada**, em `renda_laco.py`, com controle positivo. Ver "Números que caíram" nº 2. |
| 4 | Um teste afirma, lado a lado, que cegueira não deixa linha e que PARADO deixa | ✅ `test_RENDA_ZERO_E_CEGUEIRA_LADO_A_LADO_produzem_o_OPOSTO_no_disco`: 20 tiques de cada, 20 linhas contra 0, e as linhas do tique dizendo `PARADO ha` contra `PAUSADO`. |
| 5 | `git diff --name-only` sem `dashboard` nem `requirements.txt` | ✅ 7 arquivos tocados: `renda_estado.py`, `renda_laco.py`, `renda_console.py`, `captura_janela.py` e três de teste. Nenhum `.bat`, nenhum `ROADMAP.md`, nenhum `STATE.md`. |

### Critérios de sucesso

- ✅ Fechar o jogo, minimizar ou cair no login faz a tela dizer **PAUSADO com o motivo**
  e `.renda/` não ganha linha nenhuma — quatro testes, um por caminho.
- ✅ Valores bit-idênticos por tempo fazem a tela dizer **PARADO** e as linhas
  **continuam** sendo gravadas (30 tiques → 30 linhas).
- ✅ PARADO, SEM LEITURA e PAUSADO são distinguíveis **inclusive sem cor**: prefixo
  diferente na linha do tique e **marca diferente** na moldura do bloco alto.
- ✅ EXP recusado com os outros campos saindo diz `SEM LEITURA (EXP)`, congela a série
  sem consumi-la, e o `PARADO ha ...` retoma correto (`5min` depois de 19 tiques de
  recusa, contando desde a última mudança e não desde o retorno).
- ✅ O laço **não sai** por cegueira (20 frames cegos → código 0, fonte fechada) e
  religa no molde medido da party.
- ✅ `esta_minimizada` ganhou o seu primeiro chamador; **nenhuma detecção nova** foi
  escrita.

### Portões com mutação E controle

| Mutação aplicada à produção | Resultado |
|---|---|
| o ramo do quinto caso (`SEM LEITURA (EXP)`) some | 🔴 3 testes, incluindo os dois nominais |
| a recusa do EXP **zera** a série | 🔴 7 testes |
| a cegueira deixa de suspender a gravação | 🔴 5 testes |
| a cegueira **zera** o `carimbo_anterior` | 🔴 2 testes (a `lacuna` some) |
| PARADO passa a **não** gravar | 🔴 2 testes |
| PARADO e PAUSADO voltam à mesma marca | 🔴 1 teste |

| Controle (refatorar mantendo a saída) | Resultado |
|---|---|
| `motivo_da_pausa` reescrita com dicionários em vez da cadeia de `if` | 🟢 39 verdes |

## Desvios do plano

### Auto-corrigidos

**1. [Regra 3 — bloqueio] `classificar_a_visao` recebe `carimbo` e `segundos_para_parado`.**
- **Achado durante:** Tarefa 1, desenhando a ordem das chamadas.
- **O problema:** o esboço do plano dá `classificar_a_visao(*, saude, estado_do_cliente,
  minimizada, campos, rastreio)` — sem tempo —, o que obrigaria a **casca** a chamar
  `rastreio.observar(...)` antes. Mas a casca não pode decidir se a amostra deste tique
  entra na série: a resposta depende da cegueira, e **um frame `CONGELADO` devolve os
  mesmos pixels, logo os mesmos números**. Uma casca que observasse antes de perguntar
  alimentaria a série durante os 33 minutos de captura morta e sairia da cegueira
  anunciando `PARADO ha 33min` sobre um tempo em que ninguém estava vendo nada.
- **Conserto:** os dois parâmetros entram no classificador, **ambos somente-nomeados e
  sem valor de fábrica**, e a observação mora dentro dele. A decisão ficou no puro e a
  coleta na casca — que é a divisão que o próprio plano impõe.
- **Teste:** `test_a_pausa_NAO_consome_a_serie` (39 frames congelados não movem a série).
- **Commit:** `238b06c`.

**2. [Regra 3 — bloqueio] `resumo_da_sessao_da_renda` ganhou `tiques_por_estado` OBRIGATÓRIO.**
- **Achado durante:** Tarefa 3. Os quatro contadores são do resumo, e o `03-01` escreveu
  por que os parâmetros dali são obrigatórios: *"um default faria a seção sumir em
  silêncio"*.
- **Conserto:** parâmetro obrigatório, e os **três** sítios de chamada em
  `tests/test_renda_console.py` atualizados. É o único arquivo tocado fora dos
  `files_modified` do plano, e ele não pertence a nenhum plano em paralelo.
- **Commit:** `8e18f93`.

**3. [Regra 2 — correção] `duracao_curta` ficou pública.**
- `renda_estado.texto_do_parado` escreve `PARADO ha 4min` na **mesma tela** em que
  `renda_console` escreve `ha 4min` na recência da taxa. Copiar as seis linhas para o
  módulo puro seria exatamente a segunda verdade que a mudança de casa das três grafias,
  no `03-01`, existiu para impedir.
- **Commit:** `238b06c`.

### Escolhas de desenho registradas com a alternativa

**A. Dois textos por estado (`texto` curto + `aviso` alto), e não um.**
O plano pede `VisaoDaRenda(estado, motivo, texto)` com o texto acionável na linha do
tique. **Medido:** a frase acionável de minimizado tem ~240 caracteres e o orçamento da
linha é 76, dos quais os valores reais comem 53 — ela sairia como
`PAUSADO: A JANELA DO JOGO E~`, cortando exatamente a parte acionável, que é a razão de
ela existir. *Alternativa registrada:* encurtar as seis frases para caber. Custaria o
conteúdo acionável dos seis motivos por uma economia que o latch já dá de graça — o
bloco alto sai **uma vez** e a moldura cresce com o texto.

**B. A transição usa `console.moldurar` com marca por estado, e não `console.destacar`.**
O plano aponta `destacar(tipo=None)` como o caminho. Ele devolve `*` e ciano para
**todos** os estados — exatamente o colapso que o CEGO-02 proíbe (*"PARADO e PAUSADO têm
de ser distinguíveis"*). *Alternativa registrada:* reusar um `TipoDeEvento` da party por
estado da renda, o que daria marca e cor distintas — recusada porque `PARADO` viraria
`SAIU` ou `CEGUEIRA_LONGA`, uma mentira no sistema de tipos, por uma cor que
`console._pintar` desliga justamente no `scanner.log`, que é onde o usuário olha de
manhã. A distinção ficou onde ela sobrevive: **prefixo e marca**.

**C. `VisaoDaRenda.texto` é `None` no caso LENDO.**
Não é omissão: é o que faz `linha_do_tique` cair no `estado_da_leitura` do `03-01` e
continuar mostrando `nivel: campo-vazio` nos 79% de tiques em que o nível recusa com o
EXP subindo. Sobrescrever com a palavra `LENDO` trocaria a única pista de conserto na
tela por uma palavra que não ajuda.

**D. Os mapas de texto são `MappingProxyType` e não `dict`.**
O portão de ausência de memória da Fase 1 acusa literal mutável de nível de módulo, e
ele passa a varrer `renda_estado.py`. Um `dict` nu ali seria acusado — e a saída honesta
é a imutabilidade de verdade, não uma exceção de conveniência no portão.

## O achado do level up, e o que ele custou aqui

O `03-ACHADO-DO-LEVEL-UP.md` mediu, no mesmo dia, um modo de falha que **não é** cegueira
de frame: o painel de status moveu ~90 px, o retângulo do nível passou a apontar para
grama pura e o campo recusou **100%** dos tiques com o frame perfeitamente saudável.

Distinguir isso custou **uma frase**, e ela já está no produto: o aviso alto de
`SEM LEITURA` diz, com todas as letras, que *"o frame está SAUDÁVEL — o scanner está
vendo o jogo e não está conseguindo ler"* e que *"o suspeito é o RETÂNGULO e não o
brilho"*, citando a medição dos ~90 px e mandando o usuário ao `calibrar-renda.bat`.

**A varredura de piso continua sendo do `03-03` e não foi escrita aqui.** O que esta fase
garante é que quando ela chegar, o estado em que ela entra já existe e já está nomeado:
`SEM LEITURA` é frame bom + campo que não sai, que é exatamente o gatilho da varredura —
e nunca `PAUSADO`, que suspenderia a gravação sobre um jogo que está na tela.

## Contratos para o `03-03`

- `classificar_a_visao(*, saude, estado_do_cliente, minimizada, campos, rastreio, carimbo, segundos_para_parado) -> VisaoDaRenda`
- `VisaoDaRenda(estado, motivo, texto, aviso)` — `texto` é `None` em LENDO.
- `MOTIVO_DOS_CAMPOS_SEM_LEITURA` e `MOTIVO_DO_EXP_SEM_LEITURA` são os dois pontos de
  entrada naturais para o LEIT-10: a varredura de piso tem de acontecer **antes** de o
  laço aceitar um desses dois como veredito do tique.
- `SEGUNDOS_PARA_DECLARAR_PARADO` mora em `renda_laco.py`, com "ESCOLHA E NÃO MEDIÇÃO"
  escrito ao lado, no molde de `FRAMES_IDENTICOS_PARA_CONGELADO`.
- `_montar_a_fonte(titulo, entrada, *, construir_janela=None)` — a alavanca que permite
  provar o caminho da fonte sem WinRT.

## Known Stubs

Nenhum. Os dois stubs que o `03-01` registrou foram **resolvidos aqui**, que era o
combinado:

| Stub do `03-01` | Estado |
|---|---|
| `linha_do_tique(estado=None)` sem consumidor | ✅ consumido, com a assinatura intacta |
| `frame.saude` chegando ao laço e não lido | ✅ lido, e é a base do PAUSADO |

## Threat Flags

Nenhuma superfície nova fora do `<threat_model>` do plano. Os seis do registro:

- **T-03-10** (frame preto entrando como renda zero) — **mitigado**: `classificar_a_visao`
  recusa PAUSADO antes de qualquer `registrar`, com mutação provando.
- **T-03-11** (apagar evidência legítima) — **mitigado**: PARADO grava, com mutação provando.
- **T-03-12** (recusa lida como parado) — **mitigado**: três fatos separados, e a staleness
  mede o EXP (0%) e nunca o nível (79%).
- **T-03-13** (religação martelando a WGC) — **transferido e consumido sem mudar**:
  `test_recaptura.py` continua verde.
- **T-03-14** ("ficou cego a noite toda e não me disse") — **mitigado**: latch com motivo
  acionável, `lacunas_excluidas`/`segundos_em_lacuna` no bloco, e os quatro contadores no resumo.
- **T-03-15** (`matchTemplate` por tique) — **mitigado**: a cadência de 5 s mora dentro de
  `VigiaDoCliente.avaliar` e o laço **não** a reimplementa.
- **T-03-16** (`achar_janela` devolvendo a segunda instância) — **mitigado**: o hwnd vem da
  **fonte**, por `@property`, e reflete a fonte corrente depois de uma religação.

## Self-Check: PASSED

Arquivos, conferidos no disco:
- `l2scanner/renda_estado.py` — FOUND (517 linhas)
- `tests/test_renda_estado.py` — FOUND (788 linhas)
- `tests/test_renda_cegueira.py` — FOUND (1204 linhas)
- `l2scanner/renda_laco.py` — FOUND (modificado)
- `l2scanner/renda_console.py` — FOUND (modificado)
- `l2scanner/captura_janela.py` — FOUND (modificado)

Commits, conferidos em `git log`:
- `a469306` — FOUND (test: o portão dos quatro estados)
- `238b06c` — FOUND (feat: renda_estado)
- `39729bb` — FOUND (test: a pausa declarada)
- `8e18f93` — FOUND (feat: a pausa declarada, CEGO-01)
- `6ca2c94` — FOUND (feat: PARADO grava, CEGO-02)

Nenhuma deleção de arquivo rastreado em nenhum dos cinco commits
(`git diff --diff-filter=D` vazio).
