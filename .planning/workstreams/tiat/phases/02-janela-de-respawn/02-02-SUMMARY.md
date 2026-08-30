---
phase: 02-janela-de-respawn
workstream: tiat
plan: 02
subsystem: previsao-de-respawn
tags: [respawn, so-agenda, console, portoes-ast, oper-02, jane-05]
status: complete

requires:
  - "l2scanner/respawn.py :: anunciar_janelas (o contrato do plano 02-01)"
  - "l2scanner/respawn.py :: ancoras_mais_recentes, apelido_do_evento"
  - "l2scanner/agenda.py :: RegistroEmDisco.nascimentos, .marcar (O_CREAT|O_EXCL)"
  - "l2scanner/config.py :: ler_bosses"
provides:
  - "l2scanner/respawn.py :: linhas_de_previsao (pura, OPER-02)"
  - "l2scanner/__main__.py :: _avisar_janelas_de_respawn (o shell do --so-agenda)"
  - "l2scanner/__main__.py :: _anunciar_previsao_de_janelas (chamada nos DOIS lacos)"
  - "tests/test_janela_no_relogio.py :: o portao AST contra a divergencia dos dois lacos"
affects:
  - "l2scanner/__main__.py :: laco_da_agenda (a recusa por agenda vazia mudou de contrato)"
  - "l2scanner/__main__.py :: laco_principal (linha de arranque nova)"
  - "tests/test_respawn.py :: todos_os_textos() / as_quatro_frases() (separadas)"

tech-stack:
  added: []
  patterns:
    - "uma implementacao para os dois lacos, com portao AST provando os elos"
    - "proibicao de chamada com ESCOPO DE FUNCAO e nao de arquivo (enviados)"
    - "prova-nao-vazia por arvore sintatica fabricada E por mutacao do fonte real"
    - "o texto do console e o do WhatsApp citando a origem pela MESMA funcao"

key-files:
  created:
    - tests/test_janela_no_relogio.py
  modified:
    - l2scanner/respawn.py
    - l2scanner/__main__.py
    - tests/test_respawn.py

decisions:
  - "A linha de previsao usa `agora` para escolher o TEMPO VERBAL (abre/abriu, passa/passou), o que da ao parametro um uso real em vez de deixa-lo decorativo."
  - "`todos_os_textos()` foi partida em `as_quatro_frases()` + as linhas de previsao: as afirmacoes de dominio universal (D-19, ASCII, travessao) ficaram com a lista inteira e as das quatro frases (comecar pelo boss E citar o nascimento) com a lista curta. Nenhuma foi afrouxada."
  - "A repeticao do --dry-run dentro da tolerancia foi AFIRMADA como aceita, e nao consertada."

metrics:
  duration: ~55min
  completed: 2026-08-30
  tasks: 3
  commits: 6

actuals:
  tokens: 41000
  tasks: 3
  commits: 6
---

# Phase 2 Plan 02: A Janela com o Jogo Fechado, e o Portao Contra a Divergencia — Summary

A janela de respawn passa a valer no `--so-agenda` pela MESMA funcao que o laco
principal ja usava, o console dos dois lacos passa a dizer quando cada janela
abre (e a calar sobre quem nao tem ancora), e um portao AST com prova-nao-vazia
impede que os dois lacos voltem a divergir.

## O que foi construido

| Peca | Onde | O que faz |
|---|---|---|
| `_avisar_janelas_de_respawn` | `__main__.py` | o shell do `--so-agenda`: loga sempre, despacha se houver para onde, e NADA mais |
| a chamada no `while` | `laco_da_agenda` | depois de `_fechar_listas_de_presenca`, posicao fixa para o tick ser deterministico |
| a recusa estreitada | `laco_da_agenda` | so recusa quando NAO ha evento **E** NAO ha boss (T-02-14) |
| `linhas_de_previsao` | `respawn.py` | pura; uma linha por boss, na ordem do config |
| `_anunciar_previsao_de_janelas` | `__main__.py` | o shell de console, chamado nos DOIS lacos |
| o portao AST | `tests/test_janela_no_relogio.py` | os tres elos, as chamadas proibidas, e a prova de que ele morde |

---

## 1. A demonstracao ponta a ponta, sem jogo e sem rede

Pasta limpa por cena, ancora semeada A MAO com o nome literal registrado em
`02-01-SUMMARY.md`, `laco_da_agenda` de verdade rodando uma volta com o relogio
parado, `ler_agenda` devolvendo `[]` (so `[[boss]]` configurado), sem `.env`,
sem calibracao e sem captura.

```
ancora em disco: .agenda/nascimento_2026-08-30_tiat-north-1430_chat  (arquivo VAZIO)
bosses:          Tiat North (6h/8h), Tiat South (6h/8h)
```

### CENA 1 — relogio em 30/08 20:30 (`ancora + respawn_horas_min`)

```
Modo agenda: vigiando o relogio, nao a tela. Sem nenhum [[evento]] no config.toml: o que esta sendo vigiado aqui e a janela de respawn dos bosses.
O jogo NAO precisa estar aberto. O PC, sim.
Tiat North: a janela abriu em 30/08 20:30 e o limite otimista passa em 30/08 22:30, contados do nascimento que o servidor anunciou as 14:30 de 30/08.
Tiat South: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.

>>> WHATSAPP (SEMPRE):
  Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde o
  nascimento anterior, que o servidor anunciou as 14:30 de 30/08. A conta parte
  do nascimento e nao da morte, entao ele ainda pode demorar.  [20:30]

[codigo de saida: 0]  [despachos: 1]
[.agenda/: 2026-08-30_tiat-north-1430_abre, nascimento_2026-08-30_tiat-north-1430_chat]
```

### CENA 2 — relogio em 30/08 22:30 (`ancora + respawn_horas_max`)

```
>>> WHATSAPP (SEMPRE):
  Tiat North: passaram as 8h desde o nascimento anterior, que o servidor
  anunciou as 14:30 de 30/08. Esse era o limite otimista da conta, e dele para a
  frente ele pode nascer a qualquer momento: a conta parte do nascimento e nao
  da morte, entao o tempo em que o boss ficou vivo ainda nao entrou nela. [22:30]

[codigo de saida: 0]  [despachos: 1]
[.agenda/: 2026-08-30_tiat-north-1430_limite, nascimento_2026-08-30_tiat-north-1430_chat]
```

### CENA 3 — relogio em 30/08 23:30 (tres horas depois do vencimento)

```
[codigo de saida: 0]  [despachos: 0]
[.agenda/: nascimento_2026-08-30_tiat-north-1430_chat]
```

Silencio. D-22 afirmada no LACO: um aviso vencido nao ressuscita ao subir o
scanner, e nenhum arquivo de aviso foi criado.

### CENA 4 — a MESMA pasta da cena 1, segunda volta em 20:31

```
[despachos na segunda volta: 0]
[.agenda/: 2026-08-30_tiat-north-1430_abre, nascimento_2026-08-30_tiat-north-1430_chat]
```

20:31 esta DENTRO da tolerancia de cinco minutos — e onde a repeticao
aconteceria se a decisao nao fosse o `marcar`. Zero despachos, e continua um
unico arquivo de abertura.

### CENA 5 — `--dry-run`, pasta limpa e sem ancora

```
Tiat North: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.
Tiat South: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.

[codigo de saida: 0]  [despachos: 0]
[.agenda/: NAO EXISTE]
```

A `.agenda/` compartilhada nao foi tocada. Com a ancora presente
(`test_em_simulacao_o_texto_sai_e_a_pasta_nao_e_criada`), a mensagem SAI no
console e o marcador `..._abre` **nao** e gravado.

**Comando exato:** o roteiro esta em
`tests/test_janela_no_relogio.py::TestAJanelaComOJogoFechado` e
`::TestOModoDeSimulacaoNaJanela`, executaveis com
`python -m pytest tests/test_janela_no_relogio.py -q`.

---

## 2. As linhas de console, como ficaram (criterio 6 / OPER-02)

Sao as duas metades juntas. A primeira ja existia desde a Fase 1 e **nao mudou**:

```
Vigilancia de boss ativa - Tiat North, Tiat South; lendo chat e alvo a cada 2s; um aviso por nascimento.
```

A segunda e deste plano:

**Com ancora, origem ANUNCIO DO SERVIDOR:**
```
Tiat North: a janela abriu em 30/08 20:30 e o limite otimista passa em 30/08 22:30, contados do nascimento que o servidor anunciou as 14:30 de 30/08.
```

**Com ancora, origem ALVO** (a citacao muda E carrega a ressalva, D-16):
```
Tiat North: a janela abriu em 30/08 20:30 e o limite otimista passa em 30/08 22:30, contados da ultima vez que seu alvo virou Tiat North, as 14:30 de 30/08. Ter o boss no alvo nao prova nascimento, entao este numero pode estar adiantado.
```

**SEM ancora:**
```
Tiat South: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.
```

**Esta ultima linha nao contem UM UNICO DIGITO**, afirmado por
`test_a_linha_sem_ancora_nao_contem_horario_nenhum` com
`not any(c.isdigit() for c in linha)` — mais forte que "nao contem horario". O
console dizendo que nao sabe e a resposta correta (T-02-13); um horario
inventado ali seria a mesma familia de defeito que a poda de tres dias existe
para impedir, so que na tela em vez de no grupo.

O tempo verbal segue o `agora`: `abre`/`abriu`, `passa`/`passou`. E o unico uso
que a funcao pura faz do parametro, e ele e real — "a janela abre daqui a pouco"
e "a janela abriu ha duas horas" sao fatos diferentes, e um console que os
confunde manda a party sair na hora errada.

Os dois lacos emitem estas linhas no arranque, e o `--so-agenda` as repete no
mesmo bloco horario de `_anunciar_proximo`.

---

## 3. A recusa por agenda vazia mudou de comportamento para o config real?

**Nao.** Conferido executando as duas funcoes contra o `config.toml` do
repositorio, depois da mudanca:

```
eventos: 3 ['TvT', 'Prime', 'Solo Boss']
bosses : 2 ['Tiat North', 'Tiat South']
recusa ANTES  (sem evento)?            False
recusa DEPOIS (sem evento e sem boss)? False
```

O usuario tem tres `[[evento]]`, entao ele nunca caiu na recusa antiga e nao cai
na nova. **A mudanca so morde o config que ANTES era recusado e agora sobe**: um
arquivo com `[[boss]]` e nenhum `[[evento]]` — que e o publico inteiro de
JANE-05, quem vigia boss com o jogo fechado.

Afirmado nos dois sentidos, porque uma recusa apagada passaria no teste de um
sentido so:

| Config | Antes | Depois | Teste |
|---|---|---|---|
| sem evento, com boss | recusava (2) | **sobe (0)** | `test_com_boss_e_sem_evento_o_laco_sobe` |
| sem evento, sem boss | recusava (2) | recusa (2) | `test_sem_evento_e_sem_boss_o_laco_continua_recusando` |
| com evento, sem boss | subia (0) | sobe (0) | `test_com_evento_e_sem_boss_nada_mudou` |

A mensagem de erro cita as DUAS portas de entrada, afirmado por
`test_a_recusa_cita_as_DUAS_portas_de_entrada`:

```
Nao ha nada para o relogio vigiar. Crie um config.toml com pelo menos um
[[evento]] (os lembretes de horario) ou um [[boss]] (a janela de respawn).
Veja o exemplo comentado no repositorio.
```

`ler_bosses` levanta `BossInvalido` para um bloco torto e **nao e capturado
aqui** (T-02-15, `accept`): derrubar o arranque enquanto o usuario olha o console
e melhor que subir vigiando errado em silencio, e e o que o laco principal ja
faz desde a Fase 1.

---

## 4. O portao AST acusa de verdade — provado por MUTACAO do fonte real

O plano exige que o portao seja rodado contra uma copia deliberada e a acusacao
registrada, "para provar que ele nao e decoracao". Foram feitas **duas** mutacoes
no `l2scanner/__main__.py` de producao, e as duas foram revertidas.

### Mutacao A — a checagem anterior ao `marcar` (o furo que 2b fecha)

Injetado dentro de `_avisar_janelas_de_respawn`:

```python
ja_sairam = registro.enviados()
```

Acusacao:

```
FAILED tests/test_janela_no_relogio.py::TestOsDoisLacosPassamPelaMesmaImplementacao
       ::test_nenhum_shell_checa_antes_de_marcar[__main__.py-_avisar_janelas_de_respawn]
AssertionError: __main__.py::_avisar_janelas_de_respawn calcula ou checa por conta propria
assert ['enviados'] == []
```

**Um teste, nomeando a funcao.** Nenhum outro teste desta fase o veria: a
instancia com a checagem ficaria verde sozinha, e o sintoma em producao seria um
aviso **PERDIDO** — as duas instancias do usuario se veriam livres para calar
achando que a outra falou.

### Mutacao B — a copia da implementacao (o defeito WR-08 repetido)

Substituida a chamada a `anunciar_janelas` por uma reimplementacao com
`janelas_devidas` + `texto_da_janela` dentro do shell do `--so-agenda`.

Acusacao — **cinco testes**, dizendo cada elo que quebrou:

```
FAILED ...::test_o_elo_existe[__main__.py-_avisar_janelas_de_respawn-anunciar_janelas]
FAILED ...::test_nenhum_dos_dois_arquivos_calcula_por_conta_propria[janelas_devidas-__main__.py]
FAILED ...::test_nenhum_dos_dois_arquivos_calcula_por_conta_propria[texto_da_janela-__main__.py]
FAILED ...::test_nenhum_shell_checa_antes_de_marcar[__main__.py-_avisar_janelas_de_respawn]
FAILED ...::TestAJanelaComOJogoFechado::test_uma_segunda_volta_sobre_a_mesma_pasta_nao_repete
```

O ultimo e o mais eloquente: a copia perdeu o `marcar`, e a segunda volta
**repetiu o aviso** — que e literalmente o defeito que a divergencia produziria
no grupo de WhatsApp.

Depois de reverter as duas: `46 passed`.

### Prova-nao-vazia tambem por arvore fabricada

Alem da mutacao, `TestAProvaNaoEVazia` aplica o detector a arvores sintaticas
escritas a mao que contem as chamadas proibidas, e exige acusacao — e
`test_cada_nome_proibido_pega_alguma_coisa` prova que nenhum dos tres nomes
(`janelas_devidas`, `texto_da_janela`, `enviados`) e item morto com erro de
digitacao.

### O escopo de `enviados`, provado pelos DOIS lados

`enviados` e proibida **dentro do corpo** de `_avisar_janelas_de_respawn` e de
`sessao._processar_janelas`, e **nao no arquivo inteiro**:

- `test_o_laco_da_agenda_AINDA_PODE_ler_enviados` exige que
  `laco_da_agenda` continue chamando `registro.enviados()` — os avisos de agenda
  a usam desde a Fase 6, e um portao de arquivo inteiro quebraria um recurso que
  nao tem nada a ver com janela de boss. Este teste fica vermelho se alguem
  alargar o escopo sem perceber.
- `test_o_unico_leitor_de_disco_fora_de_anunciar_janelas_so_imprime` nomeia
  `_anunciar_previsao_de_janelas` como a excecao permitida e prova a razao: ela
  chama `nascimentos()` mas **nao** `marcar`, **nao** `despachar` e **nao**
  `enviados`. A proibicao de D-21 e sobre checar antes de MARCAR, e ali nao ha
  `marcar` nenhum.
- `chave_do_nascimento` fica FORA da proibicao, e a excecao esta escrita com a
  razao e afirmada:
  `test_a_escrita_da_ancora_continua_no_unico_sitio_que_tem_pixels` exige que
  `sessao._processar_bosses` a chame e que `__main__.py` **nao** a chame —
  ancorar exige pixels, e um `--so-agenda` que escrevesse ancora estaria
  inventando nascimentos.

---

## 5. O `--dry-run` repetindo dentro da tolerancia: AFIRMADO, nao consertado

Duas voltas em 20:30 e 20:31 com `--dry-run` produzem **duas** mensagens no
console. Isso e herdado de `marcar` devolver `True` sem encostar no disco quando
simula, e e exatamente o que `_processar_agenda` ja faz com os avisos de agenda.

Um contador em memoria "consertaria" isto e seria pior: trocaria ruido de
console pelo risco de o `--dry-run` **nao mostrar** justamente a mensagem que ele
existe para mostrar. Quem roda `--dry-run` esta conferindo se a mensagem sai e
como ela e escrita.

Afirmado por
`test_em_simulacao_DUAS_voltas_repetem_a_mensagem_e_isso_e_ACEITO`, para uma
mudanca futura aparecer no diff em vez de acontecer sozinha.

---

## 6. Falhas de `tests/test_mercado_*.py` no momento da execucao

Quatro problemas, **todos do workstream `mercado`**, todos atribuidos por
`git log`, **nenhum consertado e nenhum silenciado**.

| Arquivo | Sintoma | Commit responsavel |
|---|---|---|
| `tests/test_mercado_leitura.py` | `ImportError: cannot import name 'larguras_com_folga'` (coleta) | `8795b99 test(02-08)` |
| `tests/test_mercado_pagina.py` | `ImportError: cannot import name 'TETO_DA_FOLGA_DE_COLA'` (coleta) | `8795b99 test(02-08)` |
| `tests/test_calibracao_mercado.py` | `ImportError: cannot import name 'TETO_DA_FOLGA_DE_COLA'` (coleta) | `8795b99 test(02-08)` |
| `tests/test_medir_largura_de_run.py::TestOCensoEIMPORTADO::test_e_o_MESMO_OBJETO_de_medir_oclusao` | identidade de modulo `medir_oclusao` | `32d4db0 test(02-08)` / `303feed feat(02-08)` |

Os tres primeiros sao a fase RED do plano `02-08` do `mercado`, ainda em voo: os
testes ja referenciam simbolos (`larguras_com_folga`, `TETO_DA_FOLGA_DE_COLA`)
que a implementacao ainda nao exporta. O quarto e a fragilidade de identidade de
modulo que o contexto de execucao ja nomeou como pre-existente.

Nenhum toca `tiat`, `respawn.py`, `agenda.py` nem os dois lacos.

**A suite, com os tres arquivos de coleta quebrada ignorados:**

| Momento | Resultado |
|---|---|
| baseline (antes de tocar em nada) | 2246 passed, 13 skipped, **1 failed** |
| depois da Task 1 | 2262 passed, 13 skipped, 1 failed |
| depois da Task 2 | 2290 passed, 13 skipped, 1 failed |
| final | **2315 passed, 13 skipped, 1 failed** |

Comando:
```
python -m pytest tests/ -q --ignore=tests/test_mercado_leitura.py \
  --ignore=tests/test_mercado_pagina.py --ignore=tests/test_calibracao_mercado.py
```

O unico `failed` e o mesmo do baseline, do `mercado`. Os 13 skips sao os mesmos
do baseline (12 sao os testes de OCR WinRT, que pulam porque a suite roda no
`python` do sistema e nao no `.venv`). Nenhum teste foi enfraquecido, pulado ou
silenciado.

---

## Desvios do plano

### 1. [Rule 1 - Bug] Travessao em texto que o usuario le, nos dois textos NOVOS

- **Onde:** Task 1, a mensagem de recusa reescrita e a linha de arranque nova.
- **O que aconteceu:** as duas nasceram com `—`, copiando a forma do texto
  antigo. O console do Windows entregou o caractere como `�` na primeira captura
  de log, na frente do proprio teste.
- **Correcao:** `— veja o exemplo` virou `. Veja o exemplo`, e
  `config.toml — o que esta sendo vigiado` virou `config.toml: o que esta sendo
  vigiado`. A razao ficou escrita em comentario, para nao voltar.
- **Escopo:** so os textos que ESTE plano escreveu. Os travessoes pre-existentes
  em outras linhas de console de `__main__.py` sao da casa e ficaram como
  estavam — mexer neles seria uma varredura fora do escopo desta fase.
- **Commit:** `7d7f9af`.

### 2. [Rule 2 - Correcao] `todos_os_textos()` partida em duas listas

- **Onde:** Task 2, movimento 1.
- **O plano dizia:** "Acrescente as linhas de previsao ao teste parametrizado do
  portao de D-19 — a lista de tokens proibidos vale para todo texto que esta
  fase produz."
- **O que foi feito:** exatamente isso, e mais uma coisa que o plano nao
  previa. `todos_os_textos()` alimentava QUATRO testes, e um deles —
  `test_toda_frase_comeca_pelo_boss_e_cita_o_nascimento` — exige
  `"14:30 de 30/08" in texto`. A linha de previsao de um boss SEM ancora nao
  pode citar nascimento nenhum: nao ha um para citar, e inventar um e
  literalmente T-02-13.
- **Como foi resolvido, sem enfraquecer nada:** `as_quatro_frases()` foi extraida
  e passou a alimentar SO a afirmacao que e das quatro frases;
  `todos_os_textos()` = `as_quatro_frases()` + as linhas de previsao, e continua
  alimentando as tres afirmacoes de dominio universal (D-19, ASCII, travessao).
  As quatro frases continuam sendo afirmadas exatamente como antes.
- **O pedaco que SOBREVIVEU para as linhas de previsao:**
  `test_toda_linha_comeca_pelo_NOME_DO_BOSS` — D-14 vale no console tambem.
- **Alternativa recusada:** afrouxar a assercao para
  `"14:30" in texto or "ainda nao vi" in texto`. Seria uma condicao que qualquer
  texto satisfaz por acidente, e mataria o valor do teste para as quatro frases.

### 3. [Nota de execucao] Tres arquivos de mercado a mais quebrados na coleta

- **Esperado pelo contexto de execucao:** so `tests/test_mercado_leitura.py`.
- **Encontrado:** mais `tests/test_mercado_pagina.py` e
  `tests/test_calibracao_mercado.py`, os dois por
  `ImportError: cannot import name 'TETO_DA_FOLGA_DE_COLA'`.
- **Decisao:** ignorados junto com o primeiro, atribuidos ao mesmo commit
  `8795b99` do workstream `mercado`, e listados nominalmente na secao 6. Nao
  tocados.

### 4. [Nota de execucao] Um `KeyboardInterrupt` avulso numa execucao da suite

- Uma execucao da suite completa abortou com `KeyboardInterrupt` em
  `tests/test_agenda.py:1141` (o `uma_volta_so` do `_tick`, que levanta
  `KeyboardInterrupt` de proposito para o laco dar uma volta so).
- **Investigado antes de prosseguir:** `tests/test_agenda.py` isolado passou
  `144 passed`, e as duas execucoes seguintes da suite completa passaram
  (`2314` e `2315` passed). O `__main__.py` naquele momento era identico ao do
  commit anterior, que ja tinha rodado a suite verde.
- **Decisao:** classificado como interrupcao do ambiente e nao do codigo, com a
  evidencia registrada aqui em vez de silenciada.

Nenhum outro desvio.

---

## Criterios do ROADMAP atendidos por este plano

| # | Criterio | Estado |
|---|---|---|
| 2 | JANE-02 / JANE-05 — os dois avisos, tambem no `--so-agenda` | ✅ cenas 1-4, e o portao AST dos tres elos |
| 5 | JANE-06 — `--dry-run` mostra e nao queima | ✅ cena 5 + `test_em_simulacao_o_texto_sai_e_a_pasta_nao_e_criada` |
| 6 | OPER-02 — os bosses vigiados e a proxima janela; sem previsao inventada | ✅ secao 2, com a linha sem ancora provada sem digito |
| 7 | OPER-03 — tudo demonstravel com o jogo fechado e sem rede | ✅ a demonstracao inteira roda sem `.env`, sem calibracao e sem captura |
| 8 | `Categoria.SEMPRE` tambem no `--so-agenda` | ✅ `test_no_instante_da_abertura_sai_exatamente_um_despacho` |

**Risco 1 do ROADMAP ("dois lugares de fiacao, nao um") fechado por ESTRUTURA:**
os dois lacos chegam ao aviso pela mesma `respawn.anunciar_janelas`, nenhum dos
dois calcula ou checa por conta propria, e o portao AST quebra nomeando o elo se
isso mudar — provado por mutacao do fonte real, nao so por arvore fabricada.

---

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder, `TODO`/`FIXME`,
teste pulado nem `<verify>` nao executado introduzido por este plano.

O que este plano deliberadamente NAO fez, e que **nao e stub**: nao ha escrita de
ancora no `--so-agenda`. A assimetria (dois sitios de anuncio, UM de escrita) e
deliberada, esta escrita em `sessao._processar_bosses` desde 02-01 e agora e
afirmada por teste — ancorar exige pixels, e um modo sem tela que escrevesse
ancora estaria inventando nascimentos.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. A unica `high`
(T-02-10, os dois lacos divergindo) foi mitigada por estrutura com a
implementacao nomeada: uma funcao, dois shells de log-e-despacho, e o portao AST
com prova-nao-vazia por mutacao.

`T-02-15` (bloco `[[boss]]` torto derrubando um modo que antes subia) continua
`accept`, com a razao escrita em comentario no proprio `laco_da_agenda`.

## Self-Check: PASSED

- `l2scanner/respawn.py :: linhas_de_previsao` — FOUND
- `l2scanner/__main__.py :: _avisar_janelas_de_respawn` — FOUND
- `l2scanner/__main__.py :: _anunciar_previsao_de_janelas` — FOUND
- `tests/test_janela_no_relogio.py` — FOUND
- commit `65ef4e5` (test, RED Task 1) — FOUND
- commit `027dbf8` (feat, GREEN Task 1) — FOUND
- commit `8a27b50` (test, RED Task 2) — FOUND
- commit `7d7f9af` (feat, GREEN Task 2) — FOUND
- commit `a99eab5` (test, portao AST Task 3) — FOUND
- commit `7b31943` (test, o `--dry-run` afirmado) — FOUND
- `python -m pytest tests/ -q --ignore=<3 arquivos de mercado>` — 2315 passed,
  13 skipped, 1 failed (a falha do `mercado`, atribuida na secao 6)
- `python -c "import l2scanner.__main__"` — ok
- `python -c "'datetime.now' in inspect.getsource(respawn)"` — `False`
