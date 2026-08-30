---
phase: 02-janela-de-respawn
workstream: tiat
verified: 2026-08-30T23:35:49Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
suite:
  runner: ".venv/Scripts/python.exe -m pytest -q (PYTHONPATH apontando para o site-packages do Python 3.12 do sistema)"
  resultado: "2649 passed, 0 failed, 0 skipped, 2 warnings (56.94s)"
  escopo: "suite INTEIRA, sem --ignore. Os tres arquivos do workstream mercado que o contexto de execucao dizia estar em ImportError ja voltaram: rodados isolados dao 320 passed."
mutacoes_de_conferencia:
  - alvo: "l2scanner/__main__.py::_avisar_janelas_de_respawn (read-then-write reintroduzido)"
    falha_nomeada: "tests/test_janela_no_relogio.py::TestOsDoisLacosPassamPelaMesmaImplementacao::test_nenhum_shell_checa_antes_de_marcar[__main__.py-_avisar_janelas_de_respawn]"
  - alvo: "l2scanner/sessao.py::_processar_janelas (texto_da_janela calculado por conta propria)"
    falha_nomeada: "test_nenhum_dos_dois_arquivos_calcula_por_conta_propria[texto_da_janela-sessao.py] + test_nenhum_shell_checa_antes_de_marcar[sessao.py-_processar_janelas]"
  - alvo: "l2scanner/respawn.py::texto_da_janela (frase do limite passando a afirmar 'A janela fechou.')"
    falha_nomeada: "tests/test_respawn.py::TestNenhumaAfirmacaoDeEncerramento::test_nenhum_texto_desta_fase_afirma_encerramento[...]"
  - nota: "As tres mutacoes foram revertidas; `git status --porcelain l2scanner/ tests/` volta vazio."
---

# Phase 2: Janela de respawn — Relatorio de Verificacao

**Phase Goal:** A party sabe, pelo WhatsApp e com o jogo fechado, que a janela do boss abriu e que o limite otimista passou — a partir do ultimo nascimento que o scanner realmente viu, e com a mensagem dizendo de onde o numero veio.

**Verificado:** 2026-08-30T23:35:49Z
**Status:** passed
**Re-verificacao:** Nao — verificacao inicial (nao havia `02-VERIFICATION.md` anterior)

---

## Como a suite foi rodada

`.venv/Scripts/python.exe` (Python 3.12.13, com os bindings WinRT) com
`PYTHONPATH` apontando para o `site-packages` do Python 3.12 do sistema (que tem
o pytest) — o mesmo arranjo da verificacao da Fase 1.

- Suite inteira, sem nenhum `--ignore`: **2649 passed, 0 failed, 0 skipped**.
- Os tres arquivos do workstream `mercado` que o contexto de execucao reportava
  em `ImportError` de coleta (`test_mercado_leitura.py`, `test_mercado_pagina.py`,
  `test_calibracao_mercado.py`) **ja nao falham**: rodados isolados dao
  `320 passed`. O RED concorrente fechou entre a medicao do contexto e esta
  verificacao. **Nao foram tocados por mim** e nao entram no veredito desta fase.
- Nenhuma dependencia nova: `git diff 659efee..HEAD -- pyproject.toml
  requirements.txt uv.lock` e vazio.

---

## Goal Achievement

### Verdades observaveis (os 8 criterios do ROADMAP)

| # | Criterio | Status | Evidencia |
|---|---|---|---|
| 1 | JANE-01 — marcador em `.agenda/` com prefixo novo, data e boss; derrubar e subir continua do MESMO instante | ✓ VERIFICADO | Execucao propria: `registrar_nascimento` produz `nascimento_2026-08-30_tiat-north-1430_{chat,alvo,chat_e_alvo}`, todos com `st_size == 0`. `tests/test_sessao.py::TestAFatiaInteiraDaJanelaDeRespawn::test_o_anuncio_grava_exatamente_uma_ancora_com_o_nome_duravel` prova a escrita a partir de um frame; `test_um_processo_novo_sobre_a_mesma_pasta_anuncia_igual` prova que uma segunda `Sessao`, sem vigia ligado, anuncia com `14:30` no texto |
| 2 | JANE-02/JANE-05 — no `--so-agenda`, `min` produz UMA mensagem de abertura, `max` UMA de limite; nada antes de `min`; vencido nao ressuscita | ✓ VERIFICADO | Execucao propria do `laco_da_agenda` real (sem jogo, sem calibracao, sem captura, sem rede): 20:30 -> 1 despacho de abertura; 22:30 -> 1 despacho de limite; 20:29 -> `[]`; 23:30 (abertura vencida ha 3h) -> `[]`. Ver secao "Spot-checks" |
| 3 | JANE-03 — as mensagens citam o nascimento que ancorou (dia e hora), dizem que a conta parte do nascimento e nao da morte, e a de `max` NAO afirma fechamento; ha teste que recusa o texto que afirmar | ✓ VERIFICADO | As 4 frases impressas (secao "As quatro frases"): todas comecam pelo boss e contem `14:30 de 30/08`. O portao `TestNenhumaAfirmacaoDeEncerramento` roda sobre a **saida** de `texto_da_janela` e `linhas_de_previsao`, tem prova nao-vazia e prova por token. Mutacao propria: pondo `A janela fechou.` na frase do limite, a suite fica vermelha num teste NOMEADO. Ver o INFO-1 abaixo sobre uma das quatro |
| 4 | JANE-04 — nascimento novo faz os avisos do ciclo anterior nunca sairem; estrutural, sem marcador de cancelamento | ✓ VERIFICADO | `respawn.ancoras_mais_recentes` so devolve a ancora mais nova por apelido; `AvisoDeJanela.chave` sai da ANCORA e nao do alvo, entao a chave velha deixa de ser gerada. `tests/test_respawn.py::TestSoAAncoraMaisRecente::test_o_aviso_do_ciclo_velho_nunca_sai`. Valendo tambem DENTRO de um tick: `sessao.tick` chama `_processar_bosses` **antes** de `_processar_janelas` (linhas 290 e 306, com a razao escrita), afirmado por `test_ancorar_vem_antes_de_anunciar_no_mesmo_tick` |
| 5 | JANE-06 — duas instancias sobre a mesma `.agenda/` produzem exatamente um envio; reinicio dentro da tolerancia nao repete; o `marcar` E a decisao | ✓ VERIFICADO | Execucao propria: `yaza` devolve 1 aviso, `faer` 0, um `RegistroEmDisco` novo 3 minutos depois devolve 0. `agenda.marcar` usa `O_CREAT\|O_EXCL`. O portao AST proibe `enviados` **dentro dos dois shells** e a mutacao que reintroduz o read-then-write foi acusada por nome |
| 6 | OPER-02 — no arranque o console lista os bosses vigiados, diz quando a janela abre e quando o limite passa para quem tem ancora, e diz que ainda nao viu nascimento para quem nao tem, sem inventar previsao; vale tambem no `--so-agenda` | ✓ VERIFICADO | Execucao propria do `laco_da_agenda`: `Tiat North: a janela abriu em 30/08 20:30 e o limite otimista passou em 30/08 22:30, contados do nascimento que o servidor anunciou as 14:30 de 30/08.` e `Tiat South: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.` A linha sem ancora nao contem digito nenhum (`test_a_linha_sem_ancora_nao_contem_horario_nenhum`). No laco principal, `_anunciar_previsao_de_janelas` esta FORA de qualquer `if`/`try`, afirmado por AST |
| 7 | OPER-03 — `respawn.py` na tupla `MODULOS` do portao AST de relogio e portao verde; prefixo novo coberto pelo guarda de `_PREFIXOS_CONHECIDOS`; tudo demonstravel com o jogo fechado e sem rede | ✓ VERIFICADO | `tests/test_presenca.py:1264` — `MODULOS = ("agenda.py", "loot.py", "presenca.py", "bosses.py", "respawn.py")`, com prova nao-vazia POR MODULO. As duas opcoes que o ROADMAP admitia foram feitas: `PREFIXO_NASCIMENTO` declarado em `agenda.py:391` **e** dentro de `_PREFIXOS_CONHECIDOS` (linha 411), **e** `tests/test_agenda.py:1483` passou a varrer `MODULOS_COM_PREFIXO = (agenda, respawn)`. Execucao propria da poda: uma ancora de 10 dias e um aviso velho somem, a de hoje fica |
| 8 | Os avisos de janela atravessam o silencio de TvT (`Categoria.SEMPRE`) | ✓ VERIFICADO | Execucao propria: os dois despachos do `laco_da_agenda` saem com `Categoria.SEMPRE`. Em `sessao._processar_janelas` o `_despachar` passa `Categoria.SEMPRE` explicitamente; `test_sessao.py` afirma `categoria is Categoria.SEMPRE` no resultado |

**Score:** 8/8 verdades verificadas (0 presentes com comportamento nao exercitado).

---

## Os oito itens que gates anteriores marcaram

### 1. O marcador da ancora e VAZIO e o nome carrega a origem — VERIFICADO

Medido por `st_size`, e nao por leitura:

```
ITEM1 chat        nome= nascimento_2026-08-30_tiat-north-1430_chat        st_size= 0
ITEM1 alvo        nome= nascimento_2026-08-30_tiat-north-1430_alvo        st_size= 0
ITEM1 chat_e_alvo nome= nascimento_2026-08-30_tiat-north-1430_chat_e_alvo st_size= 0
```

`RegistroEmDisco.registrar_nascimento` delega inteiro a `marcar`, que faz
`os.open(alvo, O_CREAT|O_EXCL|O_WRONLY)` e fecha sem escrever byte nenhum. Nao
ha "cria e depois escreve" em lugar nenhum do caminho. `tests/test_agenda.py:1852`
(`test_o_marcador_e_VAZIO`) afirma o mesmo `st_size == 0`.

### 2. A chave do aviso sai da ANCORA, e nao do instante alvo — VERIFICADO por reproducao

Ancora as 22:00 de 30/08, abertura caindo as 04:00 de 31/08:

```
ITEM2 alvo= 2026-08-31 04:00:00   chave= 2026-08-30_tiat-north-2200_abre
```

A data da chave e a da **ancora**. E o que faz a poda de 3 dias enxergar o dia
certo e o que faz JANE-04 funcionar sem marcador de cancelamento.

### 3. `chat_e_alvo` contem sublinhados e sobrevive a volta — VERIFICADO

```
ITEM3 chave= 2026-08-30_tiat-north-1430_chat_e_alvo
      -> Ancora(boss='tiat-north', instante=2026-08-30 14:30, origem=CHAT_E_ALVO)
ITEM3 naive split len= 5   campo[2] seria= 'chat'
```

O `split("_", 2)` de `ancora_de_chave` devolve a origem inteira; um `split("_")`
ingenuo devolveria 5 campos e truncaria a origem em `chat` — a mensagem citaria
metade do sinal que ancorou, sem nada levantar. O `rpartition("-")` do campo do
meio protege o apelido com hifen (`tiat-north`) pela razao simetrica.

### 4. A mensagem de `max` nao afirma fechamento — PORTAO VERIFICADO, INCLUSIVE POR MUTACAO

- O detector `acusacoes()` roda sobre **a saida** de `texto_da_janela` e
  `linhas_de_previsao`, nunca sobre o fonte. Isso e necessario e nao estetico:
  `l2scanner/respawn.py` contem **15** ocorrencias de `fech`/`perd`, todas em
  docstrings que citam as palavras proibidas de proposito. Um `grep` de fonte
  acusaria justamente a documentacao que protege a regra.
- Prova nao-vazia presente: `test_a_prova_nao_e_vazia_o_detector_acusa_o_texto_de_controle`
  exige `acusacoes("Tiat North: a janela fechou, perdemos o boss.") == ["fech", "perd"]`,
  e `test_cada_token_da_lista_pega_alguma_coisa` exige que cada um dos seis
  tokens acuse um texto de controle proprio (nenhum item morto na lista).
- **Mutacao propria:** inseri `A janela fechou.` na frase do limite ancorada no
  anuncio. Resultado: `1 failed` em
  `TestNenhumaAfirmacaoDeEncerramento::test_nenhum_texto_desta_fase_afirma_encerramento[...]`,
  com a frase inteira no nome do teste. Revertido.

### 5. O tripwire contra a divergencia dos dois lacos — VERIFICADO NAS DUAS METADES

O escopo esta correto e e assimetrico de proposito:

- `CHAMADAS_PROIBIDAS_NOS_SHELLS = ("janelas_devidas", "texto_da_janela", "enviados")`
  — vale so dentro dos corpos de `__main__._avisar_janelas_de_respawn` e
  `sessao._processar_janelas`.
- `CHAMADAS_PROIBIDAS_NOS_ARQUIVOS = ("janelas_devidas", "texto_da_janela")`
  — `enviados` **fora**, porque `laco_da_agenda` usa `registro.enviados()` para
  os avisos de agenda desde a Fase 6.

**Morde (mutacoes proprias, ambas revertidas):**

| Mutacao no fonte real | Teste NOMEADO que quebrou |
|---|---|
| `ja_sairam = registro.enviados()` + `if aviso.chave in ja_sairam: continue` dentro de `_avisar_janelas_de_respawn` | `test_nenhum_shell_checa_antes_de_marcar[__main__.py-_avisar_janelas_de_respawn]` — `assert ['enviados'] == []` |
| `texto = texto_da_janela(aviso)` dentro de `sessao._processar_janelas` | `test_nenhum_dos_dois_arquivos_calcula_por_conta_propria[texto_da_janela-sessao.py]` **e** `test_nenhum_shell_checa_antes_de_marcar[sessao.py-_processar_janelas]` |

**E o uso da Fase 6 continua passando:** `laco_da_agenda` chama
`registro.enviados()` na chamada de `avisos_devidos` (linha 1489 de `__main__.py`)
e `test_o_laco_da_agenda_AINDA_PODE_ler_enviados` esta verde na suite —
afirmando pelo lado positivo que o escopo nao foi alargado.

Tudo isso e lido por AST e nunca por busca textual, pela mesma razao do item 4.
Ha ainda `TestAProvaNaoEVazia`, que aplica o detector a duas arvores FABRICADAS.

### 6. JANE-05 no laco do relogio — VERIFICADO POR EXECUCAO INDEPENDENTE

Rodei o `laco_da_agenda` de verdade, com harness proprio (nao o dos testes da
fase): relogio parado, agenda vazia, `ler_bosses` injetado, despachante em
memoria, `time.sleep` levantando `KeyboardInterrupt`, ancora semeada A MAO como
arquivo vazio. Sem jogo, sem calibracao, sem captura, sem rede.

```
=== 20:30 (abre = 14:30 + 6h) ===
LOG| Modo agenda: vigiando o relogio, nao a tela. Sem nenhum [[evento]] no config.toml: ...
LOG| O jogo NAO precisa estar aberto. O PC, sim.
LOG| Tiat North: a janela abriu em 30/08 20:30 e o limite otimista passa em 30/08 22:30, contados do nascimento que o servidor anunciou as 14:30 de 30/08.
LOG| Tiat South: ainda nao vi nascimento nenhum deste boss, entao nao tenho previsao de janela para ele.
DESPACHO[ Categoria.SEMPRE ]: Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde o nascimento anterior, que o servidor anunciou as 14:30 de 30/08. ...
arquivos: ['2026-08-30_tiat-north-1430_abre', 'nascimento_2026-08-30_tiat-north-1430_chat']

=== 22:30 (limite = 14:30 + 8h) ===
DESPACHO[ Categoria.SEMPRE ]: Tiat North: passaram as 8h desde o nascimento anterior, ... e dele para a frente ele pode nascer a qualquer momento: a conta parte do nascimento e nao da morte ...

=== 20:29 ===  despachos: []
=== 23:30 ===  despachos: []
```

O arquivo de aviso (`2026-08-30_tiat-north-1430_abre`) aparece na pasta ao lado
da ancora: a decisao de despacho FOI a criacao atomica.

### 7. A tolerancia de 5 minutos — VERIFICADA nas tres bordas

```
ITEM7 as 22:00 (a abertura era 19:00) -> []            # vencido ha 3h nao ressuscita
ITEM7 as 19:04:59                      -> [ABRE]        # dentro da tolerancia
ITEM7 as 19:05:00                      -> []            # fora
```

E confirmado tambem pelo laco inteiro (cena das 23:30 acima).

### 8. OPER-02 no arranque — VERIFICADO

A linha existe nos dois lacos e distingue os dois casos, com o tempo verbal
correto (`abre`/`abriu`, `passa`/`passou`) — as 20:29 sai `a janela abre em
30/08 20:30`, as 20:30 sai `a janela abriu em 30/08 20:30`. Para quem nao tem
ancora, a linha **nao contem digito nenhum** e nao inventa previsao. No
`laco_principal` a chamada esta deliberadamente fora de qualquer condicional,
para que uma calibracao quebrada nao apague a previsao de uma ancora que
continua correta em disco — afirmado por AST em
`test_o_laco_principal_anuncia_a_previsao_FORA_de_qualquer_condicao`.

---

## As quatro frases (saida real, impressa por mim)

| Origem / tipo | Texto |
|---|---|
| chat / abre | `Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde o nascimento anterior, que o servidor anunciou as 14:30 de 30/08. A conta parte do nascimento e nao da morte, entao ele ainda pode demorar.` |
| chat / limite | `Tiat North: passaram as 8h desde o nascimento anterior, que o servidor anunciou as 14:30 de 30/08. Esse era o limite otimista da conta, e dele para a frente ele pode nascer a qualquer momento: a conta parte do nascimento e nao da morte, entao o tempo em que o boss ficou vivo ainda nao entrou nela.` |
| alvo / abre | `Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde a ultima vez que seu alvo virou Tiat North, as 14:30 de 30/08. Ter o boss no alvo nao prova que ele tinha acabado de nascer, entao este numero pode estar adiantado. A conta parte do nascimento e nao da morte, entao ele ainda pode demorar.` |
| alvo / limite | `Tiat North: passaram as 8h desde a ultima vez que seu alvo virou Tiat North, as 14:30 de 30/08. Ter o boss no alvo nao prova que ele tinha acabado de nascer, entao este numero pode estar adiantado. Esse era o limite otimista da conta, e dele para a frente ele pode nascer a qualquer momento.` |

`chat_e_alvo` cai, byte a byte, no caminho do anuncio — verificado nas duas
variantes.

---

## Auditoria dos dois desvios declarados

### 02-01: as quatro mensagens escritas na Task 1 em vez de divididas — RACIOCINIO CONFIRMADO, COMPENSACAO REAL

O raciocinio se sustenta. `texto_da_janela` decide por
`ancorado_no_anuncio = aviso.ancora.origem is not OrigemDoAviso.ALVO`. Escrever
so as duas frases do anuncio na Task 1 deixaria o ramo do `ALVO` cair no texto
do anuncio, e o commit da Task 1 conteria um aviso de origem `ALVO` dizendo
**"que o servidor anunciou"** sobre um sinal que o servidor nunca anunciou. Isso
e falso exatamente no eixo que D-15/D-16 existem para proteger — a citacao da
origem **e** a ressalva, e uma ressalva errada e pior que ressalva nenhuma. A
alternativa (deixar `ALVO` levantar) poria um `raise` no caminho que anuncia
morte de party. O desvio custa menos que as duas alternativas.

O custo declarado (a Task 2 perdeu a fase RED para as quatro frases) e real e
esta dito em voz alta no SUMMARY. A compensacao declarada — conferencia por
mutacao — **foi reproduzida por mim de forma independente** (secao "item 4"): o
portao acusa uma frase de producao mutilada, com falha nomeada. Nao e uma
afirmacao de SUMMARY: e um comando que eu rodei.

### 02-02: `todos_os_textos()` partida em duas, e `test_toda_linha_comeca_pelo_NOME_DO_BOSS` — NENHUMA ASSERCAO ENFRAQUECIDA

Conferido pelo diff `git diff 3303b29 HEAD -- tests/test_respawn.py`:

- No commit 02-01, `todos_os_textos()` continha **exatamente as quatro frases** e
  nada mais. Depois da divisao, `as_quatro_frases()` produz **o mesmo conjunto**.
  `test_toda_frase_comeca_pelo_boss_e_cita_o_nascimento` passou de
  `todos_os_textos()` para `as_quatro_frases()` — parametrizacao **identica**, e
  as assercoes (`startswith("Tiat North:")` e `"14:30 de 30/08" in texto`)
  permaneceram literalmente as mesmas.
- `todos_os_textos()` **cresceu**: passou a incluir as linhas de previsao do
  console nas duas origens e nos dois casos (com ancora e sem). As tres
  afirmacoes de dominio universal — D-19 (`test_nenhum_texto_desta_fase_afirma_encerramento`),
  ASCII e travessao — passaram a cobrir mais texto do que antes.
- A metade que sobrevive para as linhas de console (`comecar pelo nome do boss`)
  ganhou teste proprio, `test_toda_linha_comeca_pelo_NOME_DO_BOSS`, afirmado
  sobre a linha COM ancora e a linha SEM.
- A alternativa que teria enfraquecido — `"14:30" in texto or "ainda nao vi" in texto`
  — foi explicitamente recusada e nao esta no codigo.

Saldo: cobertura estritamente maior, nenhuma assercao afrouxada.

---

## Artefatos exigidos

| Artefato | Esperado | Status | Detalhe |
|---|---|---|---|
| `l2scanner/respawn.py` | modulo novo: ancora, calculo, os dois avisos, os textos, a previsao de console | ✓ VERIFICADO | 524 linhas; `chave_do_nascimento`, `ancora_de_chave`, `ancoras_mais_recentes`, `janelas_devidas`, `anunciar_janelas`, `texto_da_janela`, `linhas_de_previsao`. Importa so `agenda` e `bosses` — sem ciclo |
| `l2scanner/agenda.py` | `PREFIXO_NASCIMENTO` + `registrar_nascimento` + `nascimentos`, prefixo em `_PREFIXOS_CONHECIDOS` | ✓ VERIFICADO | Linhas 391, 411, 561, 584. `registrar_nascimento` delega a `marcar` — herda `O_CREAT\|O_EXCL` e o comportamento de `--dry-run` sem reimplementar nada |
| `l2scanner/sessao.py` | `regras_de_respawn`, `_processar_janelas`, escrita da ancora em `_processar_bosses` | ✓ VERIFICADO | `_processar_janelas` chamado em `tick` linha 306, ANTES do `try/except` que retorna cedo. Unico sitio de ESCRITA de ancora do projeto |
| `l2scanner/__main__.py` | `_avisar_janelas_de_respawn` + `_anunciar_previsao_de_janelas`, fiados no `laco_da_agenda` e no `laco_principal` | ✓ VERIFICADO | Chamados em `laco_da_agenda` (linha 1546 e no bloco horario) e no arranque dos dois lacos |
| `tests/test_respawn.py` | a metade pura + o portao de D-19 | ✓ VERIFICADO | 913 linhas, 101 testes verdes |
| `tests/test_janela_no_relogio.py` | o `--so-agenda` rodando de verdade + o portao AST contra a divergencia | ✓ VERIFICADO | 915 linhas, 46 testes verdes; o harness roda `laco_da_agenda` real |
| `config.toml` | `[[boss]]` com `respawn_horas_min`/`max` (6 e 8) | ✓ VERIFICADO | `Tiat North` e `Tiat South`, 6 e 8 cada. Nao alterado nesta fase (veio da Fase 1) |

---

## Elos verificados (wiring)

| De | Para | Via | Status |
|---|---|---|---|
| `sessao._processar_janelas` | `respawn.anunciar_janelas` | chamada direta, afirmada por AST | ✓ FIADO |
| `__main__._avisar_janelas_de_respawn` | `respawn.anunciar_janelas` | chamada direta, afirmada por AST | ✓ FIADO |
| `__main__.laco_da_agenda` | `_avisar_janelas_de_respawn` | dentro do `while`, afirmado por AST | ✓ FIADO |
| `sessao._processar_bosses` | `agenda.registrar_nascimento` + `respawn.chave_do_nascimento` | unico sitio com pixels; afirmado por AST que `__main__` NAO escreve ancora | ✓ FIADO |
| `respawn.anunciar_janelas` | disco (`.agenda/`) | `registro.nascimentos()` -> `ancoras_mais_recentes` -> `janelas_devidas` -> `marcar` | ✓ FLUINDO (dado real, verificado por execucao com arquivos em `tmp`) |
| `laco_principal` / `laco_da_agenda` | `respawn.linhas_de_previsao` | `_anunciar_previsao_de_janelas`, fora de qualquer `if` no laco principal | ✓ FIADO |
| aviso de janela | WhatsApp | `despachante.despachar(moldurar(texto, hora), Categoria.SEMPRE)` nos dois lacos | ✓ FIADO |

Nenhum valor de tela vem de literal ou de mock: o instante da janela nasce de um
nome de arquivo em disco, as horas vem de `aviso.horas` (que vem do `[[boss]]`,
afirmado por `test_as_horas_saem_do_bloco_boss` com um boss inventado de 3/4h) e
o nome do boss vem do `config.toml` e nunca do OCR.

---

## Spot-checks comportamentais

| Comportamento | Comando | Resultado | Status |
|---|---|---|---|
| Marcador de ancora e vazio, nas 3 origens | script proprio com `st_size` | `0, 0, 0` | ✓ PASS |
| Chave do aviso sai da ancora, virando o dia | `janelas_devidas` as 04:00 de 31/08 | `2026-08-30_tiat-north-2200_abre` | ✓ PASS |
| `chat_e_alvo` sobrevive a ida e volta | `ancora_de_chave` | `origem=CHAT_E_ALVO` | ✓ PASS |
| Tolerancia de 5 min (3 bordas) | `janelas_devidas` | `[]` / `[ABRE]` / `[]` | ✓ PASS |
| `--so-agenda` entrega os 2 avisos | `laco_da_agenda` real, harness proprio | 1 despacho `SEMPRE` em cada instante | ✓ PASS |
| `--so-agenda` cala antes de `min` e depois da tolerancia | idem, 20:29 e 23:30 | `[]` e `[]` | ✓ PASS |
| OPER-02 nas duas metades | idem, log capturado | linha com previsao + linha "ainda nao vi" | ✓ PASS |
| JANE-06 duas instancias + reinicio | `anunciar_janelas` x3 sobre a mesma pasta | `1, 0, 0` | ✓ PASS |
| A ancora e MORTAL (poda de 3 dias) | `registro.podar(hoje=2026-08-30)` | ancora de 10 dias e aviso velho podados; a de hoje fica | ✓ PASS |
| Suite inteira | `pytest -q` (sem `--ignore`) | `2649 passed, 0 failed, 0 skipped` | ✓ PASS |

---

## Cobertura de requisitos

| Requisito | Status | Evidencia |
|---|---|---|
| JANE-01 | ✓ SATISFEITO | criterio 1; `test_um_processo_novo_sobre_a_mesma_pasta_anuncia_igual` |
| JANE-02 | ✓ SATISFEITO | criterio 2; execucao propria dos dois avisos nos dois lacos |
| JANE-03 | ✓ SATISFEITO | criterio 3; portao de D-19 provado por mutacao (ver INFO-1) |
| JANE-04 | ✓ SATISFEITO | criterio 4; estrutural, sem marcador de cancelamento; valendo dentro de um tick |
| JANE-05 | ✓ SATISFEITO | criterio 2/6; `laco_da_agenda` real, sem jogo e sem rede |
| JANE-06 | ✓ SATISFEITO | criterio 5; `O_CREAT\|O_EXCL` + portao AST contra checagem anterior |
| OPER-02 | ✓ SATISFEITO | criterio 6; nos dois lacos, com repeticao horaria no `--so-agenda` |
| OPER-03 | ✓ SATISFEITO | criterio 7; `respawn.py` no portao AST de relogio, prefixo nos dois guardas, zero dependencia nova |

Nenhum requisito orfao: os 8 mapeados para a Fase 2 no `REQUIREMENTS.md` sao os
8 declarados nos dois planos.

---

## Anti-padroes

| Arquivo | Linha | Padrao | Severidade | Impacto |
|---|---|---|---|---|
| — | — | Nenhum `TODO`/`FIXME`/`XXX`/`TBD`/`HACK`/`PLACEHOLDER` nos arquivos da fase | — | — |

Nota de leitura: `grep -E "TODO"` da positivo em `agenda.py`, `config.py` e
`__main__.py`, mas **todas** as ocorrencias sao a palavra portuguesa
`TODOS_OS_DIAS` / `TODO comando` / `TODO texto`. Nenhum marcador de debito.
`return null`/`return []` vazios: nenhum no caminho da fase — `janelas_devidas`
devolve lista vazia quando nada venceu, que e a resposta correta e nao um stub,
e `ancora_de_chave` devolve `None` de proposito para nome torto (com teste que
prova que a pasta com lixo nao derruba o laco).

---

## Observacoes (INFO — nao sao gaps)

**INFO-1. A frase `alvo / limite` e a unica das quatro que nao contem a clausula
"a conta parte do nascimento e nao da morte".** Ela carrega, no lugar, `Ter o
boss no alvo nao prova que ele tinha acabado de nascer, entao este numero pode
estar adiantado` mais `dele para a frente ele pode nascer a qualquer momento`.
Registro isto porque o criterio 3 do ROADMAP diz que as mensagens "dizem que a
contagem parte do nascimento anterior, nao da morte". Nao classifico como gap
por tres razoes, nesta ordem: (a) a redacao exata das quatro frases e
explicitamente **discricao do executor** no `02-CONTEXT.md`; (b) o
`02-01-PLAN.md` (linhas 557-563) especifica essa frase **exatamente assim**,
antes da execucao — nao houve deriva; (c) a informacao que o criterio protege —
a direcao do erro — continua legivel na frase, e por um caminho mais preciso
para essa origem: naquele ramo a ancora nao e um nascimento confirmado, entao
"a conta parte do nascimento" seria menos exato que "este numero pode estar
adiantado". Fica registrado para o usuario decidir se quer uniformizar a
redacao; nao bloqueia nada.

**INFO-2. A tabela `## Progress` do `ROADMAP.md` do workstream ainda marca
`Phase 2 — 0/2 — Planned`,** e os checkboxes das duas linhas de plano continuam
`[ ]`. E bookkeeping de artefato de planejamento, nao codigo; fica para o passo
de ship/orquestracao.

**INFO-3. Estado do workstream concorrente, atribuido e excluido.** O diff da
fase (`659efee..HEAD -- l2scanner/ tests/ config.toml`) contem tambem
`mercado_leitura.py`, `mercado_pagina.py`, `calibracao.py` e quatro fixtures de
`mercado` — trabalho do workstream `mercado` (commits `8795b99`, `31cd0ba`,
`303feed`, `5e17e52`, `f311422`). Nada disso entra no veredito desta fase e nada
disso foi tocado por mim. Ao contrario do que o contexto de execucao media, os
tres arquivos de teste do `mercado` **ja passam** (320 passed isolados), o que e
por que rodei a suite inteira sem `--ignore`.

---

## Resumo

O objetivo da fase esta verdadeiro no codigo, e nao apenas afirmado no SUMMARY.
Verifiquei por execucao — nao por leitura de bullet — que: o nascimento vira um
arquivo **vazio** cujo nome carrega dia, boss e origem; que a chave do aviso sai
da ancora e sobrevive a virada de dia; que a origem `chat_e_alvo` atravessa o
separador inteira; que o portao contra a afirmacao de fechamento roda sobre a
saida e **acusa** uma frase de producao mutilada; que o tripwire contra a
divergencia dos dois lacos morde nas duas metades e nao quebra o uso de
`enviados()` que a Fase 6 deixou; que o `--so-agenda`, com o jogo fechado e sem
rede, entrega os dois avisos e a linha de previsao; que um aviso vencido ha tres
horas nao ressuscita as 22h; e que a ancora e mortal — a poda de 3 dias a leva,
que e a garantia de ela morrer em vez de mentir.

Os dois desvios declarados foram auditados contra o diff e o plano, e nao contra
a narrativa: o de 02-01 evita um commit com afirmacao falsa de procedencia e a
compensacao por mutacao e real (reproduzida aqui); o de 02-02 nao afrouxou
nenhuma assercao — a parametrizacao da assercao estreitada e byte a byte a mesma
de antes, e as tres assercoes universais cobrem mais texto do que cobriam.

Suite inteira verde: **2649 passed, 0 failed, 0 skipped**. Arvore de trabalho
limpa depois das mutacoes de conferencia.

---

*Verificado: 2026-08-30T23:35:49Z*
*Verificador: Claude (gsd-verifier)*
