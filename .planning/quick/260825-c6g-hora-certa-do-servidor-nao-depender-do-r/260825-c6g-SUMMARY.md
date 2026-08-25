---
phase: quick-260825-c6g
plan: 01
subsystem: agenda / tempo
status: complete
tags: [relogio, agenda, dual-boot, stdlib, chatwoot]

requires:
  - l2scanner/notificador.py (USER_AGENT)
  - l2scanner/config.py (config_do_chatwoot)
provides:
  - l2scanner.relogio.Relogio (hora ancorada, imune a pulo do relogio de parede)
  - l2scanner.relogio.epoch_do_cabecalho_date
  - l2scanner.relogio.fonte_chatwoot
  - l2scanner.__main__.montar_relogio
affects:
  - l2scanner/__main__.py (as 7 chamadas de hora da agenda)
  - tests/test_silenciamento.py (uma afirmacao de fonte)

tech-stack:
  added: []
  patterns:
    - "ancora externa + avanco monotonico"
    - "fontes por parametro (mesma disciplina de agenda.py)"
    - "degradar com WARNING, nunca levantar (molde de montar_despachante)"

key-files:
  created:
    - l2scanner/relogio.py
    - tests/test_relogio.py
    - tests/test_relogio_no_laco.py
  modified:
    - l2scanner/__main__.py
    - tests/test_silenciamento.py

decisions:
  - "A hora vem do cabecalho Date da resposta HTTP do Chatwoot — zero dependencia, zero porta nova."
  - "A ancora e presa ao PONTO MEDIO da requisicao, nao ao fim."
  - "A requisicao de ancoragem NAO manda o token: qualquer resposta HTTP traz Date, inclusive 401/404."
  - "epoch_do_cabecalho_date recusa ano < 2020 — um proxy quebrado nao pode reancorar o scanner em 1970."
  - "montar_relogio recebe `fonte` por parametro para o teste offline nao encostar no .env real."

metrics:
  duration: ~35min (incluindo a retomada da execucao interrompida)
  completed: 2026-08-25

actuals:
  tokens: 7900
  tasks: 3
  commits: 4
---

# Quick 260825-c6g: Hora certa do servidor — nao depender do relogio do PC

O scanner parou de perguntar as horas para um relogio que mente: a hora da
agenda agora e ancorada no servidor do Chatwoot e avanca pelo monotonico, entao
um pulo de 3h no Windows nao move mais o horario de TvT/Prime.

## O que foi feito

**O bug real.** O PC do usuario e dual boot. O Linux grava o relogio do hardware
em UTC, o Windows le o mesmo valor como hora local, e ao voltar do Linux o
Windows fica ~3h adiantado ate se corrigir sozinho. A deteccao nunca esteve em
risco — debounce, cooldown e staleness usam `time.monotonic()`, que nao pula.
Quem quebrava era a **agenda**: ela le a hora de parede a cada tick e so dispara
dentro de `TOLERANCIA_MINUTOS = 5` depois do alvo, entao um erro de 3h atravessa
a janela inteira sem toca-la. O aviso de TvT nao saia **nenhuma vez, em
silencio**.

**`l2scanner/relogio.py` (novo, 209 linhas, stdlib pura).**

- `epoch_do_cabecalho_date` — le o `Date` RFC 7231, devolve `None` para lixo, e
  recusa ano < 2020. Nunca levanta.
- `Relogio` — `fonte`, `monotonico` e `parede` entram por parametro (a mesma
  disciplina de `agenda.py`, e o motivo de nenhum teste precisar de rede ou
  `monkeypatch`). `sincronizar()` ancora no ponto medio da viagem;
  `agora_epoch()` soma o delta monotonico a ancora; sem ancora cai no relogio da
  maquina. `confiavel` e `desvio_do_windows()` alimentam a mensagem de arranque.
  `iniciar_sincronizacao_periodica()` reancora numa thread daemon — o laco de
  captura nunca pode bloquear em rede.
- `fonte_chatwoot` — `GET` na URL base, **sem token**, com o `USER_AGENT` do
  notificador (o Chatwoot do usuario esta atras do Cloudflare, que barra o UA
  padrao do urllib com erro 1010). `HTTPError` tambem serve como sucesso: ele
  expoe `.headers`, entao um 404 ancora igual. `TIMEOUT_ANCORA = 3.0`.

**`l2scanner/__main__.py` — a fiacao.** `montar_relogio(args, fonte=None)`
espelha `montar_despachante`: monta, degrada com WARNING, e **nunca levanta**.
Sincroniza uma vez, sincrono, antes do laco — se a primeira volta rodasse com o
relogio torto, ela poderia gravar um marcador de "ja avisei" com a chave errada,
e o marcador e duravel. As 7 chamadas de hora da agenda passaram a vir do
relogio ancorado:

| Lugar | Antes | Depois |
|---|---|---|
| `laco_principal` (o seam do `momento`) | `time.time()` | `relogio.agora_epoch()` |
| `laco_principal` (proxima ocorrencia) | `datetime.now()` | `relogio.agora()` |
| `laco_da_agenda` (`ultimo_anuncio`, `agora`) | `datetime.now()` x2 | `relogio.agora()` |
| `_anunciar_proximo` | `datetime.now()` x2 | parametro `relogio` |
| `comando_teste_de_agenda` | `datetime.now()` | `relogio.agora()` |
| `comando_cancelar_silencio` | `datetime.now()` | `relogio.agora()` |

Nao sobrou nenhum `.now()` no arquivo (gate automatizado). Os `destacar(texto)`
sem hora ganharam `hora=...`.

**Mensagens de arranque**, verificadas ao vivo:

```
WARNING O relogio do Windows esta ADIANTADO 3h02min em relacao ao servidor - a agenda vai usar a hora do servidor.
WARNING Causa provavel: dual boot. O Linux grava o relogio do hardware em UTC e o Windows le o mesmo valor como hora local.
```
```
WARNING A hora do servidor nao veio - usando o relogio do Windows.
WARNING Se voce acabou de voltar do Linux, o horario de TvT/Prime pode sair errado ate o Windows se corrigir sozinho.
```

**Testes (25 novos).** `tests/test_relogio.py` (19) prova as propriedades do
modulo — inclusive o pulo de +3h depois da ancora. `tests/test_relogio_no_laco.py`
(6) prova a outra metade pelo nucleo testavel (`Sessao.tick`): com a hora
ancorada o aviso de TvT sai, com a hora torta do Windows ele **morre em
silencio**, e `montar_relogio` degrada sem levantar com fonte morta e sem `.env`.

## Verificacao

| Gate | Resultado |
|---|---|
| `pytest tests/test_relogio.py tests/test_relogio_no_laco.py -q` | 25 passed |
| Gate de imports (so stdlib + `l2scanner`) | ok |
| Gate `.now()` / seam do `momento` / precedencia do replay | ok |
| `git diff --name-only` nos arquivos de deteccao | vazio |
| Nenhum `time.monotonic()` existente alterado | confirmado por diff |
| `ruff check` nos 5 arquivos tocados | limpo |
| `montar_relogio` contra o Chatwoot real | ancorou; desvio 0.151s |
| Suite inteira | **485 passed, 6 failed** |

**Os numeros, honestamente.** Baseline antes desta tarefa: 466 testes, dos quais
**6 ja falhavam**. Agora: 491 testes, 485 passando e **os mesmos 6 falhando**.
Nenhuma regressao; +25 testes novos.

## Desvios do plano

**1. [Regra 1 — Teste desatualizado] `tests/test_silenciamento.py::test_o_modo_so_agenda_usa_o_relogio_mesmo`**

- **Encontrado em:** Task 2
- **Problema:** o teste afirmava `"agora = datetime.now()" in fonte` de
  `laco_da_agenda` — exatamente a linha que este plano existe para eliminar.
- **Correcao:** a afirmacao passou a exigir `"agora = relogio.agora()"` e ganhou
  a trava inversa (`"datetime.now()" not in fonte`). A **intencao** do teste
  ("la nao existe frame, entao o relogio e a unica fonte de tempo") foi
  preservada e ficou mais forte: agora ele falha se alguem voltar a perguntar as
  horas ao Windows.
- **Commit:** `316e62f`

**2. [Nenhuma correcao — fora de escopo] 6 testes de `test_agenda.py`**

Pre-existentes, causados por deriva do `config.toml` do usuario (um TvT as 19:30
que os testes nao esperam). Verificado que falham identicamente sem as mudancas
deste plano. Registrados em `deferred-items.md`, nao corrigidos: a regra de
escopo so autoriza corrigir o que a propria tarefa quebrou. O `config.toml`
modificado na arvore de trabalho e edicao do usuario e **nao foi commitado nem
revertido**.

## Verificacao manual que sobra para o usuario

Itens 2 e 3 da `<verification>` do plano exigem desligar o Wi-Fi e observar o
arranque — nao executaveis aqui. Substituidos por testes automatizados
equivalentes (`TestArranqueSemRede`) e pelo exercicio ao vivo de
`montar_relogio` contra o Chatwoot real. O que resta e confirmatorio:

```
python -m l2scanner --so-agenda --dry-run
```

Com o Wi-Fi desligado tem que SUBIR e anunciar o proximo evento normalmente,
imprimindo o WARNING de que a hora do servidor nao veio.

## Notas

- **Zero dependencia nova.** Somente `time`, `datetime`, `email.utils`,
  `logging`, `threading`, `urllib` — gate automatizado no plano.
- **Nenhum stub.** Nenhum `TODO`, `FIXME` ou teste pulado foi introduzido.
- **`config.toml`** aparece modificado em `git status`: edicao do usuario,
  intocada por esta tarefa.

## Self-Check: PASSED

- `l2scanner/relogio.py` — FOUND
- `l2scanner/__main__.py` — FOUND
- `tests/test_relogio.py` — FOUND
- `tests/test_relogio_no_laco.py` — FOUND
- `.planning/quick/260825-c6g-hora-certa-do-servidor-nao-depender-do-r/deferred-items.md` — FOUND
- commit `b96007d` — FOUND
- commit `0c952c3` — FOUND
- commit `316e62f` — FOUND
- commit `e116374` — FOUND
