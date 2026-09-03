---
phase: 03-o-modo-renda-o-painel-ao-vivo-e-a-cegueira-declarada
plan: 04
subsystem: renda
tags: [lancador, bat, higiene, roadmap, CONS-02, C-9, W1]
status: complete

requires:
  - "__main__.py::--renda e o portao da mira (03-01, mesclado)"
  - config.ler_personagem_do_jogo
  - cliente.SEPARADOR / cliente.NOME_DO_CLIENTE
  - vigiar-mercado.bat  # o arquivo copiado
provides:
  - vigiar-renda.bat                  # a quarta invocacao, processo separado
  - tests/test_vigiar_renda_bat.py    # dezessete portoes, tres controles positivos
  - "ROADMAP.md: Progress e Coverage conferidos contra o disco"
  - "ROADMAP.md: a ressalva datada do criterio 4 (rotulos invertidos, W1)"
affects:
  - 03-03  # a ressalva M-Y muda o que a varredura tem de dizer ao perder em TODOS os pisos

requirements-completed: [CONS-02]

tech-stack:
  added: []          # NENHUMA dependencia nova. `rich` continua fora.
  patterns:
    - "lancador como COPIA do irmao com trocas contadas, e nenhuma melhoria oportunista"
    - "portao de texto sobre .bat COM controle positivo sintetico"
    - "Coverage DERIVADA do REQUIREMENTS.md, e nao emendada"
    - "ressalva datada AO LADO do criterio, nunca reescrita dele"

key-files:
  created:
    - vigiar-renda.bat
    - tests/test_vigiar_renda_bat.py
  modified:
    - .planning/workstreams/renda/ROADMAP.md

decisions:
  - "o .bat foi GERADO por script a partir do irmao, para que a copia dos blocos estruturais fosse literal por construcao e nao por transcricao"
  - "o portao herdado `\"ler_personagem_do_jogo\" in texto` foi trocado: ele PASSA sobre um .bat mutado para ignorar a chave do config"
  - "o duodecimo teste (python do .venv por caminho literal) entra, e por razao propria: o defeito de 2026-08-31 foi o Python global sem OCR"
  - "a fraqueza do portao irmao NAO foi consertada no arquivo do mercado: fora do escopo deste plano, registrada abaixo"

metrics:
  duration: "~1h"
  completed: 2026-09-03

actuals:
  tokens: 7673       # chars/4 sobre as 702 linhas adicionadas
  tasks: 3
  commits: 3
---

# Phase 3 Plan 04: O lançador e a higiene do roadmap — Summary

`vigiar-renda.bat` — a **quarta invocação**, em processo separado, cópia de `vigiar-mercado.bat`
com quatro trocas e nenhuma quinta — mais dezessete portões de texto sobre ele (com três
controles positivos), e um `ROADMAP.md` que parou de errar a própria contagem e de afirmar um
gloss que o código contradiz.

## O que foi construído

| Peça | Arquivo | O que faz |
|---|---|---|
| O lançador | `vigiar-renda.bat` (184 linhas) | Dois cliques → `-m l2scanner --renda --janela "%JANELA%" %*`. Processo separado. |
| Os portões | `tests/test_vigiar_renda_bat.py` (440 linhas) | 17 testes: os 11 da família, 3 novos, 3 controles positivos. |
| A higiene | `.planning/workstreams/renda/ROADMAP.md` | `Progress`, `Coverage`, e as ressalvas datadas do critério 4, do LEIT-10 e do REND-08. |

### As quatro trocas, e nenhuma quinta

O `.bat` foi **gerado por script** a partir de `vigiar-mercado.bat`, e essa escolha é o que
torna a promessa "cópia literal fora das quatro trocas" **verificável e não afirmada**: o
script assere que cada trecho a trocar aparece **exatamente uma vez** antes de trocá-lo, e tudo
que ele não nomeia atravessa byte a byte. Atravessaram intactos: `@echo off` / `setlocal` /
`cd /d "%~dp0"`; a busca do Python em cinco lugares guardando o caminho completo; a rejeição do
stub da Microsoft Store; a criação do `.venv`; a sonda de dependências; a resolução de
`--janela` pelo `for /f`; e os blocos `:erro_venv` / `:erro_deps` **antes** da execução.

| # | O que trocou |
|---|---|
| 1 | O cabeçalho `REM`: o que ele é (a quarta invocação, processo separado), o que **não** é (não vigia a party, não lê o mercado, não envia alerta), o que precisa antes (`calibrar-renda.bat` e `calibrar-renda-moldes.bat`), e que o produto é a `.renda\` com o CSV **e** o `LEIAME.txt` (C-10) |
| 2 | `--mercado` → `--renda` na única linha de execução |
| 3 | O texto da sonda de OCR e o da recusa da mira — que agora aponta para `calibrar-renda.bat` |
| 4 | **Nada de `--personagem`**: o nome sai do título, como `renda_modo.py:330` já faz |

## Números que foram medidos, e não afirmados

### 1. O piso da suíte neste worktree é 5851, e não os 5838 do checkout principal

**Medido no commit base, com a árvore limpa:** `17 failed, 5851 passed, 24 skipped,
145 deselected`. O prompt dá **5838 passed** no checkout principal.

E as **17** falhas do piso não são as 15 nomeadas: além das bombas-relógio de `date.today()`
(`test_sessao`, `test_janela_no_relogio`, `test_respawn`), o piso trouxe
`test_dashboard_servidor.py::test_a_origem_AUSENTE_e_recusada_com_403` e
`test_janela_de_selecao.py::test_dreno_por_tempo_e_nao_por_numero_de_sondagens`. **As duas
voltaram verdes na rodada final sem que nada nelas fosse tocado** — são intermitentes por
tempo, e não regressões. Nenhum arquivo de `dashboard` foi tocado por este plano.

### 2. A bateria de oito mutações: os oito portões acusam

Nenhum portão deste plano afirma existência; cada um foi quebrado de propósito e voltou
vermelho antes de ser aceito.

| Mutação aplicada ao `vigiar-renda.bat` | Resultado |
|---|---|
| a linha de execução volta a ser `--mercado` | 🔴 7 testes |
| um `echo` de encerramento depois da execução | 🔴 1 teste |
| o conselho certo some do `echo` da recusa | 🔴 1 teste |
| o conselho vira `vigiar-party.bat` (o defeito de 2026-08-31) | 🔴 2 testes |
| `--personagem` entra na linha de execução | 🔴 2 testes |
| `--janela` vai pelado | 🔴 1 teste |
| `--replay` entra na linha de execução | 🔴 2 testes |
| a mira deixa de vir da chave do config | 🔴 1 teste *(só depois do conserto abaixo)* |

E os quatro portões da Tarefa 3, pela mesma disciplina:

| Mutação aplicada ao `ROADMAP.md` | Resultado |
|---|---|
| LEIT-10 sai da `Coverage` | 🔴 `requisitos fora da Coverage: ['LEIT-10']` |
| REND-08 e REND-09 saem da `Coverage` | 🔴 os dois nomeados |
| a Fase 1 volta a dizer *Not started* | 🔴 `Progress ainda diz Not started` |
| a ressalva do critério 4 some | 🔴 `o criterio 4 saiu sem a ressalva dos rotulos invertidos (W1)` |

### 3. O portão herdado da mira PASSAVA sobre um `.bat` que ignora o config

Este é o achado da bateria, e ele derruba um teste que já estava na árvore.

O guarda irmão pergunta `"ler_personagem_do_jogo" in texto`. **Medido:** com o `.bat` mutado de
`print((ler_personagem_do_jogo() or sys.argv[1]) + ...)` para `print(sys.argv[1] + ...)` — um
lançador que **ignora a chave do config e mira sempre o nome escrito à mão** —, os dezessete
testes ficaram **verdes**. O nome sobrevive na cláusula `import` da mesma linha, e a busca por
substring no arquivo inteiro não distingue *importar* de *chamar*.

É exatamente a família de defeito que a docstring deste arquivo já contava sobre `REM`: uma
guarda enganada pelo próprio texto que a acompanha. **Conserto (Regra 1):** a afirmação passa a
ser sobre a **linha que monta `JANELA`** e sobre a **chamada com parênteses**
(`ler_personagem_do_jogo()`), e as duas constantes do título (`SEPARADOR`, `NOME_DO_CLIENTE`)
passam a ser exigidas **naquela linha**, e não em qualquer lugar do arquivo. Com o conserto, a
mutação fica vermelha.

## O `ROADMAP.md`: o que era falso, e o que passou a ser conferido

| Onde | Dizia | Diz agora |
|---|---|---|
| `Progress`, Fase 1 | *0/? · Not started · -* | **5/5 · Complete · 2026-09-02** |
| `Progress`, Fase 2 | *0/? · Not started · -* | **4/4 · Complete · 2026-09-03** |
| `Progress`, Fase 3 | *0/? · Not started · -* | **2/4 · Em execução** |
| `Coverage` | 23 linhas | **27 linhas**, uma por requisito do `REQUIREMENTS.md` |
| `Coverage`, rodapé | *"18 de 18 requisitos mapeados"* | **"27 de 27"** — 9 na Fase 1, 13 na Fase 2, 5 na Fase 3 |

Os quatro que faltavam entraram: **LEIT-10** (Fase 3), **LEIT-11**, **REND-08** e **REND-09**
(Fase 2). As datas saem dos próprios SUMMARY e nenhuma foi inventada. A `Coverage` foi
**derivada** varrendo os `- [ ] **XXX-NN**` do `REQUIREMENTS.md` — não emendada, porque uma
tabela emendada herda o erro que ninguém viu.

**LEIT-11 ganhou nota de rodapé**: a dona é a Fase 2 (as regras de par são a defesa principal e
moram lá) e a Fase 3 carrega a obrigação **negativa** de não chamá-las — o laço fala com
`renda_conta`, e `tests/test_renda_par.py:703` prende isso. São os dois lados da mesma
fronteira, e a nota existe justamente para que ninguém leia isso como um requisito em duas
fases.

**A lista dos quatro planos da Fase 3 foi conferida contra o disco** e confere: quatro arquivos
`03-0N-PLAN.md`, com `wave:` **1 / 2 / 3 / 2** lidos das frontmatter. A execução não acrescentou
nem renumerou nada.

### As três ressalvas datadas, e por que nenhuma reescreve o texto que corrige

Todas as três ficam **ao lado** do original, no molde literal da que derrubou o `rich.Live` no
critério 1. Um argumento refutado que some é um argumento que volta.

**(a) O critério 4 — W1, os rótulos invertidos.** O roadmap define *"parado é o scanner não
estar vendo"*; o código desta fase faz o **inverso**, porque o `03-CONTEXT.md:56-66` prevalece:

| rótulo | o critério 4 | o código |
|---|---|---|
| **PARADO** | o scanner não está vendo | estou vendo e o valor não mudou — **grava** |
| **PAUSADO** | (não nomeado) | não consigo ver — **não grava** |

A **substância** do critério continua entregue e não se mexe: valores bit-idênticos ganham
rótulo próprio, e ele é distinguível de renda zero na tela. O que está trocado é qual palavra
recebe qual fato — e *pausado* já é a palavra que o `REQUIREMENTS.md:307` e o critério 3 logo
acima usam para *não estou enxergando*. Deixar a fase fechar com o gloss trocado seria pior que
o roadmap calar: o próximo leitor confia nele e depura na direção errada.

**(b) O critério 5 — M-Y, o LEIT-10 não cobre um painel MOVIDO.** Do
`03-ACHADO-DO-LEVEL-UP.md`, medido hoje rodando o `--renda` de verdade: o painel de status andou
~90 px, o retângulo gravado passou a apontar para grama pura, e o nível recusou **100%** dos
tiques. Nenhum piso, em nenhum alcance, lê um número num retângulo que contém grama. Brilho pede
**varredura**; posição pede **recalibrar** — e os dois se parecem de fora. **Consequência escrita
para o `03-03`**: perder em *todos* os pisos do alcance não é só motivo de cegueira, é o sinal de
que o suspeito é o **retângulo**, e a mensagem tem de mandar o usuário ao calibrador.

**(c) O bloco do REND-08 — M-Z, a ponte do 67 virou histórica no mesmo dia.** A Faerlina subiu
para o 68 e `renda_ponte_de_xp` só tem `Faerlina/67`: o XP absoluto sai **declaradamente
indisponível** até alguém medir o 68 — que é o REND-08 funcionando. A ressalva escreve o tamanho
do erro que a regra evita (~17% de subestimação do XP/h, um número plausível e errado) e registra
que a ferramenta que mede a ponte, listada como *ideia adiada* com a nota "ela vira necessária no
próximo level up", **deixou de ser adiável** — o level up aconteceu no mesmo dia.

## Desvios do plano

### Auto-corrigidos

**1. [Regra 1 — defeito] O portão da mira não acusava um `.bat` que ignora o config.**
Ver "Números que foram medidos" nº 3. Encontrado pela bateria de mutações, não por leitura.
- **Achado durante:** Tarefa 2, na oitava mutação.
- **Conserto:** a afirmação passa a ser sobre a linha que monta `JANELA` e sobre a chamada com
  parênteses; as duas constantes do título passam a ser exigidas naquela linha.
- **Commit:** `2190c08`.

### O que a versão anterior do plano prometia e não existia — já corrigido no planejamento

**Não há `**Plans**: TBD` neste arquivo e não havia.** `ROADMAP.md:450` já dizia
`**Plans**: 4 planos escritos` com a lista dos quatro. O portão que acompanhava a promessa
(`'TBD' not in road`) passava hoje, com a fase inteira por executar — os dois saíram na revisão
do plano, e o trabalho que sobrou (conferir a lista contra o disco) foi feito e está acima.

### Decisões de escopo registradas com a alternativa

**O teste do `.venv` por caminho literal entrou.** O `<read_first>` mandava *decidir* se ele
vale aqui. Vale, e por razão própria e não por simetria: o defeito de 2026-08-31 foi o modo
rodado pelo **Python global**, onde o OCR não existe. O caminho literal é o que torna aquele
desfecho impossível por este lançador — é a mitigação de `T-03-28` escrita como teste.
*Alternativa registrada:* deixá-lo de fora por ser "do `ponte-bat`". Custaria o único portão que
mede a mitigação daquela ameaça.

**A ressalva do critério 4 é verificada por checagem executável, e não por teste versionado.**
O `<behavior>` pedia *"um teste ou uma checagem executável"*. A checagem do `<verify>` foi
rodada com **controle positivo** (remover a ressalva a deixa vermelha, acima). Um teste
versionado exigiria um arquivo fora dos três de `files_modified` — e o `03-02` corre em paralelo.
*Alternativa registrada:* pendurar a checagem em `tests/test_vigiar_renda_bat.py`. Poria uma
afirmação sobre o `ROADMAP.md` num arquivo cujo assunto é o `.bat`, e o próximo leitor não a
acharia.

## Deferred Issues

**O mesmo defeito do portão da mira vive em `tests/test_vigiar_mercado_bat.py`.** Aquele arquivo
pergunta `"ler_personagem_do_jogo" in texto` e passaria, pela mesma razão, sobre um
`vigiar-mercado.bat` mutado para ignorar a chave do config. **Não foi consertado**: está fora dos
três arquivos de `files_modified` deste plano, o defeito é pré-existente e não foi causado por
nada aqui, e o `03-02` corre em paralelo nesta árvore. O conserto é a troca de quatro linhas já
escrita em `tests/test_vigiar_renda_bat.py`, e cabe num `/gsd-quick`.

*(Registrado aqui e não em `deferred-items.md`: aquele arquivo é compartilhado e este plano roda
num worktree paralelo — escrever nele criaria um conflito de mesclagem por uma nota.)*

## Verificação

| # | Verificação do plano | Resultado |
|---|---|---|
| 1 | `pytest tests/test_vigiar_renda_bat.py tests/test_vigiar_mercado_bat.py -q` | ✅ **28 passed** (17 + 11) |
| 2 | Suíte inteira `>=` piso, mesmas falhas pré-existentes | ✅ **15 failed, 5870 passed** — **+19** sobre o piso de 5851, e as 15 são exatamente as bombas-relógio de `date.today()`. As outras duas do piso voltaram verdes sozinhas. |
| 3 | A checagem compara `REQUIREMENTS.md` com a `Coverage` e não acha requisito de fora | ✅ `coverage ok: 27 requisitos` — e **zero órfãos** na direção contrária também |
| 4 | `## Progress` não diz mais *Not started*, com a checagem **recortada naquela seção** | ✅ passa, e a mutação que reintroduz o rótulo fica vermelha. O critério 4 sai com a ressalva encostada nele. |
| 5 | `git diff --name-only` lista **três** arquivos e nenhum em `l2scanner/` | ✅ `ROADMAP.md`, `tests/test_vigiar_renda_bat.py`, `vigiar-renda.bat` |

### Critérios de sucesso

- ✅ `vigiar-renda.bat` existe, é **ASCII puro** (zero bytes > 127), roda `--renda --janela` numa
  linha só, resolve a mira pela chave do config, recusa quando ela não monta com `pause` e
  `exit /b 1`, e **não imprime nada** depois da execução.
- ✅ Os dezessete portões passam, com os **três** controles positivos (as flags só dentro de um
  `REM` devolvem `-1`; `REM echo` não conta como impressão; um `echo` depois da execução **é**
  acusado).
- ✅ Nenhuma mensagem manda rodar `vigiar-party.bat`, `vigiar-mercado.bat` nem `calibrar.bat`, e o
  conselho certo — `calibrar-renda.bat` — **aparece** num `echo`.
- ✅ O `ROADMAP.md` deixou de dizer *Not started* sobre fases mescladas; a `Coverage` inclui
  LEIT-10, LEIT-11, REND-08 e REND-09; a lista dos quatro planos confere com o disco.
- ✅ O critério 4 carrega a ressalva datada dos rótulos invertidos, **ao lado** do texto original.
- ✅ Nenhuma dependência nova, nenhum arquivo de `l2scanner/`, nenhum arquivo do `dashboard`,
  `requirements.txt` intacto.

## Known Stubs

Nenhum. Não há valor vazio, texto de espera nem componente sem fonte de dados neste plano — os
três artefatos são um `.bat`, um arquivo de testes e documentação, e os três estão inteiros.

## O que ficou para o portão humano

O **critério 2 da fase** — *"quatro invocações, quatro janelas, nenhuma dependendo da outra"* —
**não tem teste automatizado, e não deveria ter**: é uma propriedade do sistema operacional com
quatro processos vivos e o jogo aberto, e nenhum número desta árvore a alcança. O roteiro está no
`<human-check>` do `03-04-PLAN.md`, e ele é de **fim de fase**: subir os quatro `.bat`, fechar o
do `--renda`, conferir que os outros três continuam escrevendo, subir de novo e fechar o do
mercado, conferir quatro `python.exe` distintos no Gerenciador de Tarefas, e olhar a `.renda/`
atrás do CSV **e** do `LEIAME.txt`.

O que este plano **pode** afirmar sozinho está afirmado: o lançador é um `.bat` próprio, com
`.venv` próprio e linha de execução própria, e nada nele encosta em outro processo.

## Threat Flags

Nenhuma superfície nova fora do `<threat_model>` do plano. As mitigações escritas lá viraram
teste, uma a uma:

| Ameaça | Como ficou medida |
|---|---|
| T-03-23 (mirar a instância errada) | `--janela` com valor, mira da chave do config **na linha que monta `JANELA`**, e nenhum `--personagem` — três testes, todos com mutação vermelha |
| T-03-24 / T-03-25 (destino de arquivo, `--replay`) | varredura de dez nomes de flag; a mutação com `--replay` fica vermelha |
| T-03-26 (anunciar o que não conferiu) | nenhum `echo` depois da execução, helper que ignora `REM`, **com** controle positivo |
| T-03-27 (conselho da feature errada) | proibidos os três lançadores das outras features, **e exigido** o certo |
| T-03-28 (Python de fora do `.venv`) | teste do caminho literal `".venv\Scripts\python.exe" -m l2scanner --renda` |
| T-03-29 (cobertura que não tem) | `Coverage` derivada do `REQUIREMENTS.md`, com checagem executável e quatro mutações vermelhas |
| T-03-SC (instalação de pacote) | não se aplica: nada instalado, `requirements.txt` intacto |

## Self-Check: PASSED

Arquivos, conferidos no disco:
- `vigiar-renda.bat` — FOUND (184 linhas, 0 bytes não-ASCII)
- `tests/test_vigiar_renda_bat.py` — FOUND (440 linhas, 17 testes)
- `.planning/workstreams/renda/ROADMAP.md` — FOUND (633 linhas, +78/−4)

Commits, conferidos em `git log`:
- `0d45224` — FOUND — `feat(03-04): vigiar-renda.bat, copia do irmao do mercado com quatro trocas`
- `2190c08` — FOUND — `test(03-04): os dezessete portoes do vigiar-renda.bat, com controle positivo`
- `d61b3df` — FOUND — `docs(03-04): o ROADMAP para de mentir sobre si mesmo, e o criterio 4 ganha ressalva`
