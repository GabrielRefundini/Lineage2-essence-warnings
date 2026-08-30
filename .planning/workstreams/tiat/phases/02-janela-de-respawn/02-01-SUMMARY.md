---
phase: 02-janela-de-respawn
workstream: tiat
plan: 01
subsystem: previsao-de-respawn
tags: [respawn, agenda, disco, ancora, whatsapp, portoes]
status: complete

requires:
  - "l2scanner/agenda.py :: RegistroEmDisco.marcar (O_CREAT|O_EXCL)"
  - "l2scanner/agenda.py :: apelido_do_evento"
  - "l2scanner/bosses.py :: Boss, OrigemDoAviso, AvisoDeBoss"
provides:
  - "l2scanner/respawn.py :: anunciar_janelas (o contrato que o plano 02-02 consome)"
  - "l2scanner/respawn.py :: chave_do_nascimento, ancora_de_chave, ancoras_mais_recentes"
  - "l2scanner/respawn.py :: janelas_devidas, texto_da_janela, TipoDeJanela, Ancora, AvisoDeJanela"
  - "l2scanner/agenda.py :: PREFIXO_NASCIMENTO, RegistroEmDisco.registrar_nascimento, .nascimentos"
  - "l2scanner/sessao.py :: Sessao.regras_de_respawn, _processar_janelas, ResultadoDoTick.{ancoras_gravadas,avisos_de_janela}"
affects:
  - "l2scanner/config.py :: _recusar_bosses_repetidos (contrato do config.toml mudou)"
  - "tests/test_presenca.py :: TestSemRelogioProprio.MODULOS"
  - "tests/test_agenda.py :: TestPodaAlcancaTodosOsPrefixos.MODULOS_COM_PREFIXO"

tech-stack:
  added: []
  patterns:
    - "logica de tempo extraida do laco numa funcao pura, no molde de presenca.fechar_ocorrencias"
    - "uma implementacao para os dois lacos (anunciar_janelas), no molde de presenca.fechar_e_narrar"
    - "marcador vazio com O_CREAT|O_EXCL como decisao de despacho inteira"
    - "cancelamento por AUSENCIA de chave, e nao por marcador de cancelamento"
    - "portao de texto rodando sobre a SAIDA das funcoes, nunca sobre o fonte"

key-files:
  created:
    - l2scanner/respawn.py
    - tests/test_respawn.py
  modified:
    - l2scanner/agenda.py
    - l2scanner/sessao.py
    - l2scanner/config.py
    - l2scanner/__main__.py
    - tests/test_agenda.py
    - tests/test_sessao.py
    - tests/test_presenca.py
    - tests/test_bosses.py

decisions:
  - "As quatro frases foram escritas na Task 1 em vez de duas na Task 1 e duas na Task 2, para nao existir commit em que a origem ALVO produza um texto que atribui a citacao ao servidor."
  - "A justificativa do tipo proprio (R-2) NAO mudou durante a execucao."
  - "O desempate de origem no mesmo minuto usa peso ALVO=0 < CHAT=1 < CHAT_E_ALVO=2, para ser total e nao so parcial."

metrics:
  duration: ~50min
  completed: 2026-08-30
  tasks: 3
  commits: 4

actuals:
  tokens: 74000
  tasks: 3
  commits: 4
---

# Phase 2 Plan 01: A Janela de Respawn no Laco Principal — Summary

O scanner passa a PREVER: um nascimento visto na tela as 14:30 vira um arquivo
vazio em `.agenda/`, e seis horas depois esse arquivo — sem tela, sem rede,
possivelmente noutro processo — vira uma mensagem no grupo que cita o
nascimento e diz qual sinal o produziu.

## O que foi construido

A fatia vertical inteira dentro do laco principal, mais os tres portoes
estruturais que impedem a fase de nascer com um buraco.

| Peca | Onde | O que faz |
|---|---|---|
| `respawn.py` | modulo novo, 427 linhas | toda a logica de tempo, pura, sem relogio proprio |
| `PREFIXO_NASCIMENTO` + `registrar_nascimento`/`nascimentos` | `agenda.py` | o namespace da ancora, no molde de `cancelar`/`cancelados` |
| a escrita da ancora | `sessao._processar_bosses` | o UNICO sitio de escrita de ancora do projeto |
| `_processar_janelas` | `sessao.py` | o anuncio, com `Categoria.SEMPRE` |
| `regras_de_respawn` | `Sessao.__init__` + `__main__.py` | kwarg separado de `bosses`, uma leitura so de `ler_bosses()` |

---

## 1. Os dois formatos de chave, como ficaram gravados

Conferidos contra a tabela de D-18, caractere a caractere. **O plano 02-02 e a
verificacao da fase leem estes formatos daqui**, e `tests/test_janela_no_relogio.py`
semeia a ancora com o nome literal.

| Namespace | Forma gravada | Exemplo real |
|---|---|---|
| ancora de nascimento | `nascimento_<YYYY-MM-DD>_<boss-slug>-<HHMM>_<origem>` | `nascimento_2026-08-30_tiat-north-1430_chat` |
| aviso de janela | `<YYYY-MM-DD>_<boss-slug>-<HHMM>_<tipo>` (sem prefixo) | `2026-08-30_tiat-north-1430_abre` |

- `<origem>` ∈ `chat`, `alvo`, `chat_e_alvo` — o `.value` de `bosses.OrigemDoAviso`.
- `<tipo>` ∈ `abre`, `limite` — o `.value` de `respawn.TipoDeJanela`.
- A data e a hora sao **sempre as da ANCORA**, nos dois namespaces, inclusive
  na chave do aviso. Afirmado por
  `TestAChaveDoAvisoSaiDaAncora::test_a_data_da_chave_e_a_da_ancora_mesmo_virando_o_dia`:
  uma ancora das 22:00 abre as 04:00 do dia seguinte e a chave continua
  dizendo `2026-08-30_`.
- **O marcador e VAZIO.** Afirmado por tamanho de arquivo
  (`test_o_marcador_e_VAZIO`, `st_size == 0`), e nao so por inspecao visual.

**Uma armadilha de parsing que o formato tem e que foi resolvida:** a origem
`chat_e_alvo` contem sublinhados, que sao o proprio separador. `ancora_de_chave`
parte com `split("_", 2)` (tres campos, maxsplit=2) e o campo do meio com
`rpartition("-")` — porque o apelido tambem contem hifens (`tiat-north`). Um
`split("_")` ingenuo devolveria cinco campos e a origem voltaria truncada em
`chat`, fazendo a mensagem citar metade do sinal que ancorou, sem levantar nada.

---

## 2. A justificativa do tipo proprio (R-2)

**Nao mudou durante a execucao.** As quatro razoes escritas no plano para
`respawn.TipoDeJanela` existir em vez de `agenda.TipoDeAviso` ganhar
`ABRE`/`LIMITE` continuam valendo exatamente como escritas, e a implementacao
confirmou a quarta:

- `avisos_devidos` recebe `list[EventoAgendado]` e deriva de regra de
  CALENDARIO; `janelas_devidas` recebe `dict[str, Ancora]` lido de DISCO mais
  `list[Boss]`, e deriva de regra em horas relativas. As assinaturas nao se
  encontram sem a funcao deixar de ser pura.
- O filtro de `eventos_calados` casa por `apelido_do_evento(evento.nome)` —
  um boss cujo apelido coincidisse com um evento calado perderia os avisos de
  janela sem ninguem ter desligado boss nenhum.
- **O que E compartilhado ficou compartilhado**: a convencao de chave, produzida
  pelo mesmo `apelido_do_evento`. Isso rendeu o que prometia — `podar` alcanca os
  dois namespaces novos **sem uma linha de codigo nova**, e o teste parametrizado
  de poda ganhou quatro casos (`nascimento_…_chat`, `nascimento_…_chat_e_alvo`,
  `…_abre`, `…_limite`) que passam contra o `podar` que ja existia.
- A colisao concebivel (um `[[evento]]` chamado como um `[[boss]]`, no mesmo
  minuto) esta afirmada como impossivel por
  `test_os_sufixos_de_tipo_nao_colidem_com_os_da_agenda`, que compara os dois
  enums e exige interseccao vazia.

---

## 3. O portao de D-19, e as quatro frases

### A lista de tokens proibidos

Vive em `tests/test_respawn.py::TOKENS_PROIBIDOS`. **O plano 02-02 acrescenta as
linhas de previsao do console a este mesmo portao** — `todos_os_textos()` e uma
lista justamente para isso: acrescentar a quinta origem de texto e acrescentar
um item, e nao escrever um segundo portao que pode divergir deste.

```python
TOKENS_PROIBIDOS = (
    "fech", "perd", "tarde demais",
    "ultima chance", "nao nasce mais", "passou da hora",
)
```

Sao RADICAIS e nao palavras inteiras: `fech` pega "fechou"/"fechada"/"fecha",
`perd` pega "perdemos"/"perdeu"/"perda". O detector roda **sobre a saida das
funcoes e nunca sobre o arquivo-fonte** — as docstrings de `respawn.py` citam as
palavras proibidas de proposito, para explicar a proibicao por escrito, e uma
varredura do fonte acusaria justamente a documentacao que protege a regra.

**A prova nao e vazia, e foi conferida de duas formas:**
1. `test_a_prova_nao_e_vazia_o_detector_acusa_o_texto_de_controle` — o texto de
   controle `"Tiat North: a janela fechou, perdemos o boss."` e acusado com
   `["fech", "perd"]`; e `test_cada_token_da_lista_pega_alguma_coisa` prova que
   nenhum dos seis tokens e item morto.
2. **Por mutacao, durante a execucao**: trocada a frase do limite em
   `respawn.py` por uma que afirma encerramento, a suite ficou vermelha em 2
   testes (o portao de tokens e a afirmacao do piso). Revertida, verde de novo.

### As quatro frases, como ficaram

**ABRE, ancorada no anuncio**
> Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde o nascimento anterior, que o servidor anunciou as 14:30 de 30/08. A conta parte do nascimento e nao da morte, entao ele ainda pode demorar.

**LIMITE, ancorado no anuncio**
> Tiat North: passaram as 8h desde o nascimento anterior, que o servidor anunciou as 14:30 de 30/08. Esse era o limite otimista da conta, e dele para a frente ele pode nascer a qualquer momento: a conta parte do nascimento e nao da morte, entao o tempo em que o boss ficou vivo ainda nao entrou nela.

**ABRE, ancorada no alvo**
> Tiat North: a janela abriu. Antes de agora ele nao nascia; sao 6h desde a ultima vez que seu alvo virou Tiat North, as 14:30 de 30/08. Ter o boss no alvo nao prova que ele tinha acabado de nascer, entao este numero pode estar adiantado. A conta parte do nascimento e nao da morte, entao ele ainda pode demorar.

**LIMITE, ancorado no alvo**
> Tiat North: passaram as 8h desde a ultima vez que seu alvo virou Tiat North, as 14:30 de 30/08. Ter o boss no alvo nao prova que ele tinha acabado de nascer, entao este numero pode estar adiantado. Esse era o limite otimista da conta, e dele para a frente ele pode nascer a qualquer momento.

`CHAT_E_ALVO` cai no caminho do ANUNCIO — afirmado por igualdade de string com o
texto de `CHAT`, e nao por inspecao. As horas (`6h`, `8h`) saem de `aviso.horas`,
que veio do `[[boss]]`; um boss de 3h/4.5h produz `3h`/`4.5h`, afirmado.

---

## 4. A assinatura de `anunciar_janelas` — o contrato do plano 02-02

```python
def anunciar_janelas(
    registro,                    # agenda.RegistroEmDisco
    bosses: Iterable[Boss],      # as regras do config.toml
    agora: datetime,             # o tempo entra por parametro. Sempre.
) -> list[tuple[AvisoDeJanela, str]]:
```

Devolve **so os avisos que ESTE processo ganhou** — os que voltaram `True` do
`registro.marcar(aviso.chave)` — ja pareados com o texto pronto. O que fica com
o chamador e o que e dele: o log, a moldura, o despacho e o `ResultadoDoTick`.

O plano 02-02 consome isto do outro lado (`--so-agenda`) e **nao precisa de mais
nada**: nao ha escrita de ancora do lado dele, e a assimetria e deliberada —
ancorar exige pixels, anunciar exige so o relogio e o disco.

`AvisoDeJanela` carrega `boss` (o nome do config), `tipo`, `ancora`, `alvo`,
`horas`, e a property `chave`.

---

## 5. `[[boss]]` do config.toml recusados pela nova regra

**Nenhum.** Conferido executando `ler_bosses()` sobre o `config.toml` real do
repositorio depois da mudanca:

```
'Tiat North' -> tiat-north  6.0 8.0
'Tiat South' -> tiat-south  6.0 8.0
```

Os dois apelidos sao distintos e nao-vazios, entao o arranque do usuario nao
mudou. A regra nova so morde nomes que ja seriam ambiguos em disco (`Tiat  North`
com espaco duplo, `Tiat-North`, `Tiat North!`, `tiat.north` — todos parametrizados
como recusa) e nomes sem nenhuma letra ou numero (`"!!!"`).

Guarda contra prova vazia incluida: `Tiat North` + `Tiat South` no mesmo arquivo
continuam subindo, senao uma recusa que rejeitasse tudo passaria nos testes de
recusa.

---

## 6. Falhas de `tests/test_mercado_*.py` no momento da execucao

**Nenhuma.** A suite inteira ficou verde.

O plano antecipava ~40 falhas de mercado atribuidas a commits `02-06`/`02-07` do
outro workstream. Elas **nao apareceram neste worktree**, e a razao e estrutural:
o worktree e um checkout limpo do commit base, enquanto as 40 falhas medidas na
verificacao da Fase 1 vinham de **edicoes nao commitadas na arvore de trabalho do
checkout principal** (`git status` do repo principal mostra `_olhar_tela.py`,
`calibration.*.json` e outros arquivos sujos). Nao ha nada a atribuir por
`git log` porque nao ha falha.

| Momento | Resultado |
|---|---|
| baseline (antes de tocar em nada) | 2359 passed, 14 skipped |
| depois da Task 1 | 2419 passed, 14 skipped |
| final (depois da Task 3) | **2483 passed, 14 skipped** |

Os 14 skips sao os mesmos do baseline. **12 deles sao os testes de OCR WinRT**,
que pulam porque a suite roda no `python` do sistema (tem pytest, nao tem as
bindings WinRT) e nao no `.venv` — exatamente o que o contexto de execucao
previa. `2359 + 12 = 2371`, que e a contagem do checkout principal.

Nenhum teste foi enfraquecido, pulado ou silenciado.

---

## Desvios do plano

### 1. [Rule 2 - Correcao] As quatro frases foram escritas na Task 1, e nao duas na Task 1 e duas na Task 2

- **Onde:** Task 1, movimento 3 (`texto_da_janela`).
- **O plano dizia:** "texto_da_janela fica nesta tarefa com as DUAS frases do
  caminho ancorado no anuncio; a Task 2 acrescenta as duas do caminho ancorado
  no alvo."
- **O que foi feito:** as quatro foram escritas na Task 1.
- **Por que:** seguir a letra produziria um commit — o da Task 1 — em que um
  aviso com origem `ALVO` cairia no ramo do anuncio e diria **"que o servidor
  anunciou"** sobre um sinal que o servidor nunca anunciou. Isso e uma afirmacao
  falsa sobre a procedencia do dado, no exato eixo que D-15/D-16 existem para
  proteger: a citacao da origem E a ressalva, e uma ressalva errada e pior que
  ressalva nenhuma. A alternativa (deixar `ALVO` levantar) poria uma excecao no
  laco que anuncia morte de party.
- **Custo, dito em voz alta:** a Task 2 perdeu a fase RED. Os testes de texto
  dela nasceram verdes porque o codigo ja existia. **A Task 2 nao virou vazia** —
  ela entregou o portao de D-19, a prova nao-vazia dele, o teste por token, a
  guarda de acento/travessao, as horas vindas do `[[boss]]` e as arestas de tempo
  que faltavam. Mas o valor especifico de "ver o teste falhar antes" foi perdido
  para as quatro frases, e a compensacao foi a **conferencia por mutacao**
  registrada na secao 3: o portao foi provado quebrando o codigo de producao de
  proposito e vendo a suite ficar vermelha.

### 2. [Nota de execucao] A base do worktree estava um commit a frente do esperado

- **Esperado:** `659efee`. **Encontrado:** `65f6d8c`.
- **Investigado antes de prosseguir:** `659efee` e ancestral direto de `65f6d8c`,
  e o unico commit de diferenca (`docs(02-08)`) toca **tres arquivos, todos em
  `.planning/workstreams/mercado/`** — o workstream que este plano tem proibicao
  explicita de tocar. Zero sobreposicao com `tiat` ou `l2scanner`.
- **Decisao:** prosseguir. A assercao existe para pegar um worktree construido
  sobre codigo ERRADO; aqui ela e um avanco benigno de documentos de outro
  workstream, e parar custaria uma ida ao humano por um no-op.

Nenhum outro desvio. Os formatos de D-18 foram implementados exatamente como a
tabela manda; nenhuma porta de mao unica foi reaberta.

---

## Os tres portoes, e o que cada um passou a impedir

| Portao | Onde | O modo de falha que ele fecha |
|---|---|---|
| relogio proprio | `TestSemRelogioProprio.MODULOS` += `respawn.py` | um `datetime.now()` faria os testes continuarem verdes passando um `agora` que o codigo ja nao usaria — e aqui o instante tambem veio de DISCO, entao a divergencia produz previsao ERRADA e nao aviso faltando |
| ancora imortal | `MODULOS_COM_PREFIXO = (agenda, respawn)` | um `PREFIXO_*` declarado fora de `agenda.py` escapava de `vars(agenda)` e nascia imortal — e uma ancora velha nao ocupa disco em silencio, ela PRODUZ janelas erradas com cara de certas |
| apelido colidindo | `_recusar_bosses_repetidos` += eixo do apelido | dois nomes distintos para o `casefold` virando o mesmo `tiat-north` em disco, dividindo a MESMA ancora, com o nascimento de um reiniciando a contagem do outro |

Os tres ganharam **prova nao-vazia**, porque um portao que nao pode falhar nao e
portao:
- o de relogio agora injeta `datetime.now()` no fonte REAL de cada um dos cinco
  modulos e exige acusacao (antes so provava sobre um fonte de mentira);
- o de prefixos e testado contra um namespace de mentira com um `PREFIXO_*`
  nao classificado;
- o de apelido e testado contra o par legitimo `Tiat North`/`Tiat South`, que
  tem que continuar subindo.

---

## Criterios do ROADMAP atendidos

| # | Criterio | Estado |
|---|---|---|
| 1 | JANE-01 — ancora em `.agenda/`, contagem sobrevive a processo novo | ✅ `test_um_processo_novo_sobre_a_mesma_pasta_anuncia_igual` |
| 2 | JANE-02 — os dois avisos, com as bordas de tolerancia | ✅ no laco principal (o `--so-agenda` e do 02-02) |
| 3 | JANE-03 — citam nascimento e origem; teste recusa encerramento | ✅ portao de D-19 com prova por mutacao |
| 4 | JANE-04 — estrutural, sem marcador de cancelamento | ✅ inclusive DENTRO de um unico tick |
| 5 | JANE-06 — dois registros, um envio | ✅ `test_duas_instancias_produzem_exatamente_um_par` |
| 7 | OPER-03 — portoes, jogo fechado, sem rede | ✅ os tres, com prova nao-vazia |
| 8 | `Categoria.SEMPRE` afirmada em `resultado.despachos` | ✅ |

---

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder, `TODO`/`FIXME`,
teste pulado nem `<verify>` nao executado introduzido por este plano.

O que este plano deliberadamente NAO fez, e que **nao e stub porque esta no
escopo declarado do plano 02-02**: a fiacao do `--so-agenda` (`laco_da_agenda`),
a linha de previsao no console e a mensagem de arranque. `anunciar_janelas` ja
existe e e a unica implementacao que os dois lacos vao chamar.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. As cinco ameacas
`high` (T-02-01 a T-02-05) foram mitigadas com a implementacao nomeada:
poda alcancando o prefixo novo, origem citada na mensagem, reancoragem
estrutural, lista de permissao do apelido afirmada por teste de travessia de
caminho, e recusa de arranque para apelidos colidentes.

## Self-Check: PASSED

- `l2scanner/respawn.py` — FOUND
- `tests/test_respawn.py` — FOUND
- `.planning/workstreams/tiat/phases/02-janela-de-respawn/02-01-SUMMARY.md` — FOUND
- commit `1116fca` (test, RED) — FOUND
- commit `85f5d81` (feat, GREEN/tracer) — FOUND
- commit `3303b29` (test, portao D-19) — FOUND
- commit `b5f8a1b` (test, os tres portoes) — FOUND
- `python -m pytest tests/ -q` — 2483 passed, 14 skipped, 0 failed
- `python -c "import l2scanner.__main__"` — ok
- `python -c "'datetime.now' in inspect.getsource(respawn)"` — `False`
