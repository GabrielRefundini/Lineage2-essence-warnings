---
phase: quick-260825-ehc
plan: 01
subsystem: loot
tags: [loot, comandos, whatsapp, estatistica, historico]
status: complete

requires:
  - l2scanner/loot.py (RegistroDeLoot, apelido, descrever_momento, eh_solo_boss)
  - l2scanner/comandos.py (interpretar_dinamico, _NICK_VALIDO)
provides:
  - Comando.LOOT_CORRIGIR
  - RegistroDeLoot.corrigir()
  - Correcao (dataclass)
  - responder_correcao()
affects:
  - l2scanner/__main__.py (atender_comandos)

tech-stack:
  added: []
  patterns:
    - "tri-estado de string em vez de booleano, herdado do `_criar`"
    - "criar-antes-de-apagar como desenho da falha, nao como estilo"
    - "funcao `responder_*` pura, tempo por parametro"
    - "ramo com hifen + ramo de duas palavras, sempre em par"

key-files:
  created: []
  modified:
    - l2scanner/loot.py
    - l2scanner/comandos.py
    - l2scanner/__main__.py
    - tests/test_loot.py
    - tests/test_comandos.py

decisions:
  - "A ordem criar-antes-de-apagar e a especificacao, nao uma preferencia: os tres desfechos possiveis foram escolhidos por qual deles o usuario consegue consertar."
  - "A guarda do mesmo apelido e o unico ponto entre um no-op e a destruicao do registro — provado por mutacao, nao so por leitura."
  - "O ramo de duas palavras nasce junto do ramo com hifen, por regra, depois do bug do `.loot cancelar`."

metrics:
  duration: ~25min
  completed: 2026-08-25
  tests_before: 581
  tests_after: 598

actuals:
  tokens: 6044
  tasks: 3
  commits: 4
---

# Quick 260825-ehc: Corrigir um loot ja consumado Summary

`.corrigir-<nick>` (e `.corrigir <nick>`) troca pelo WhatsApp o dono do loot de
Solo Boss mais recente ja consumado, com a troca aparecendo nos dois lados do
`.<nick>` e sem nenhum caminho em que o loot suma.

## O que mudou

O caso real que abriu a tarefa: o boss das 10:00 passou, a designacao era do
TioMad, o `consumir()` gravou `pegou_2026-08-25-1000_tiomad` — mas quem pegou
foi o Kaus. Nao havia caminho nenhum pelo WhatsApp. O `cancelar()` nao encosta
nos `pegou_*` de proposito (cancelar e sobre a VEZ, nao sobre o HISTORICO), e a
unica saida era renomear o arquivo a mao no Explorer.

Rodado de ponta a ponta contra o cenario exato do objetivo:

```
antes  TioMad: TioMad pegou 1 loot de Solo Boss. Ultimo: hoje as 10:00.
antes  Kaus  : Kaus ainda nao pegou nenhum loot de Solo Boss.
resposta     : O loot do Solo Boss de hoje as 10:00 passou do Tiomad para o Kaus.
depois TioMad: TioMad ainda nao pegou nenhum loot de Solo Boss.
depois Kaus  : Kaus pegou 1 loot de Solo Boss. Ultimo: hoje as 10:00.
no-op        : O loot do Solo Boss de hoje as 10:00 JA era do Kaus — nada mudou.
arquivos     : ['nick_kaus', 'nick_tiomad', 'pegou_2026-08-25-1000_kaus']
```

| Peca | Onde | O que faz |
|---|---|---|
| `Correcao` | `loot.py` | Tri-estado-e-meia: `corrigido` / `mesmo_dono` / `sem_registro` / `falhou` |
| `RegistroDeLoot.corrigir()` | `loot.py` | A troca. Nunca levanta, nunca devolve `None` |
| `responder_correcao()` | `loot.py` | O texto que nomeia boss, momento, dono antigo e novo |
| `Comando.LOOT_CORRIGIR` | `comandos.py` | O unico comando que reescreve HISTORICO |
| dois ramos de `.corrigir` | `comandos.py` | Hifen e duas palavras; `.corrigir` sozinho e `None` |
| dispatch | `__main__.py` | `avisar_o_grupo = False` |

## As duas linhas onde este trabalho podia destruir dado

Ambas foram conferidas **por mutacao**, nao por leitura — escrevi a versao
errada de propósito e verifiquei que a suite reclama:

| Mutacao aplicada | Testes que quebraram |
|---|---|
| Remover a guarda `apelido(nick) == anterior` | 3 (incluindo o da invariante, que mostrou o registro destruido) |
| Inverter a ordem: apagar antes de criar | 2 (incluindo `falha_de_disco_NAO_apaga_o_velho`) |

Isso importa porque os dois bugs sao **silenciosos**: sem a guarda, corrigir
para o mesmo apelido devolveria uma resposta de sucesso enquanto apagava o
unico registro que existia. Um teste que so lesse o valor de retorno nao veria
nada de errado.

A ordem final, verificada no arquivo: guarda (linha 321) -> `_criar` (324) ->
`unlink` (335).

## Decisoes que valem registrar

**A ordem criar-antes-de-apagar foi escolhida pelo desfecho consertavel.** Os
tres resultados possiveis nao sao equivalentes: falha no criar deixa tudo como
estava; falha no apagar deixa um duplicado, que aparece no `.<nick>` e some com
outro `.corrigir`; a ordem inversa perde o loot em silencio. Numa estatistica
sem poda e sem backup, o unico criterio que importa e qual erro o usuario
consegue ver e desfazer.

**O `estado == "ja_existia"` segue para o apagar de propósito.** Ele so acontece
quando o alvo tinha dois donos registrados — exatamente o duplicado que a regra
acima aceita deixar para tras. Apagar o velho ali e o conserto, nao a perda. Tem
teste proprio (`test_o_duplicado_COLAPSA`).

**O ramo de duas palavras nao e conveniencia.** O RED provou o mecanismo: com
`nicks_conhecidos={"corrigir"}`, o `.corrigir` sozinho retornava
`(LOOT_CONSULTA, "corrigir")` — a mesma classe de bug do `.loot cancelar` da
tarefa anterior, que designava um personagem chamado "cancelar". O `return None`
explicito no fim do ramo e o que fecha isso.

**Limitacao aceita e documentada no codigo:** o dono antigo sai slug-cased
("Tiomad", nao "TioMad") porque o nome do arquivo e o unico registro que existe
dele. Restaurar a caixa exigiria adivinhar, e um nome adivinhado numa rede de
seguranca vale menos que um nome feio e honesto.

## Deviations from Plan

**1. [Rule 3 - Blocking] `test_o_vocabulario_e_fechado` precisou do membro novo**
- **Found during:** Task 1
- **Issue:** O teste-tripwire que assere `set(Comando)` exato falhou ao entrar o `LOOT_CORRIGIR`. Nao estava na lista de arquivos do plano.
- **Fix:** Acrescentado o membro com o comentario que a propria docstring do teste pede ("quando ela crescer, e para crescer de proposito"), registrando que este e o de maior alcance da lista e qual e o contrapeso.
- **Commit:** a372a4c

**2. Task 2 nasceu verde, e o plano previu isso**
- O plano dizia que os testes de `mesmo_dono` e `falhou` deveriam falhar antes da implementacao, "se o Task 1 os tiver deixado como esboco". O Task 1 implementou os quatro ramos de texto por inteiro, entao os sete testes do Task 2 passaram de primeira.
- **Nenhum foi pulado** — o plano e explicito que eles sao a armadura contra regressao. Para nao aceitar cobertura de fachada, rodei as duas mutacoes destrutivas descritas acima; foi o que provou que os testes mordem.

## Verification

| Passo | Resultado |
|---|---|
| `python -m pytest -q` | 598 passed (581 antes, +17) |
| `python -m pytest tests/test_loot.py -q -k Correcao` | 9 passed |
| `ruff check` nos 5 arquivos | All checks passed |
| Ordem das linhas criticas no diff | guarda -> criar -> apagar, conferida |
| Mutacao: sem guarda / ordem invertida | 3 e 2 testes quebram, respectivamente |
| Cenario do objetivo, ponta a ponta | reproduzido acima |

Tudo sem o jogo aberto e sem rede.

## Success Criteria

- [x] `.corrigir-kaus` e `.corrigir kaus` trocam o dono do loot mais recente
- [x] A troca aparece nos dois lados do `.<nick>`
- [x] `.corrigir` sozinho nao faz nada, nem com um nick "corrigir" existente
- [x] Corrigir para o mesmo apelido nao apaga nada
- [x] Sobra sempre um `pegou_` para o alvo, nos quatro desfechos
- [x] Sem registro nenhum: resposta honesta, sem excecao
- [x] A resposta nomeia boss, momento, dono antigo e dono novo
- [x] Sai so na conversa de origem, sem eco no grupo
- [x] 581+ testes passando (598)

## Known Stubs

Nenhum. Nao ha `TODO`, `FIXME`, teste pulado ou `<verify>` nao rodado nesta
tarefa.

## Fora de escopo, como combinado

O `cancelar()` continua sem encostar em `pegou_*`, e o `.corrigir` continua sem
encostar em `proximo.json`. Sao dois comandos sobre duas coisas diferentes — a
VEZ e o HISTORICO.

## O que nao esta coberto

Nenhum teste roda contra o Chatwoot real. A costura vai ate `atender_comandos`
com um `LeitorFalso` e um `NotificadorEmMemoria`, que e onde a suite inteira
para — consistente com o resto do projeto, e a razao pela qual o `__main__.py`
e o arquivo de menor cobertura. O primeiro `.corrigir` mandado do celular ainda
e a primeira vez que este caminho ve a rede.

## Self-Check: PASSED

Arquivos conferidos (todos FOUND): `l2scanner/loot.py`, `l2scanner/comandos.py`,
`l2scanner/__main__.py`, `tests/test_loot.py`, `tests/test_comandos.py`.

Commits conferidos (todos FOUND):

| Task | Commit | Assunto |
|---|---|---|
| 1 (RED) | `f128a2f` | test(ehc-01): a troca nos dois lados e a guarda que apaga tudo |
| 1 (GREEN) | `a372a4c` | feat(ehc-01): `.corrigir-<nick>` de ponta a ponta |
| 2 | `e776602` | test(ehc-02): as invariantes que protegem a estatistica |
| 3 | `5efbc01` | feat(ehc-03): duas palavras, e a porta dos fundos fechada |

## TDD Gate Compliance

Sequencia completa e na ordem: `test(ehc-01)` (RED, falhou por `ImportError`)
-> `feat(ehc-01)` (GREEN) -> `test(ehc-02)` -> `feat(ehc-03)` (RED verificado
antes, com as duas falhas registradas). Sem passo de REFACTOR: nao houve
duplicacao a limpar depois do verde.
