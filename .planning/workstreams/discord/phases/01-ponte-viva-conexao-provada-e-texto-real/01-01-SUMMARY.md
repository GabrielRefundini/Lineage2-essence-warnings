---
phase: 01-ponte-viva-conexao-provada-e-texto-real
plan: 01
subsystem: integracao
tags: [discord.py, gateway, asyncio, tomllib, dotenv-a-mao, stdlib, pytest]

requires: []
provides:
  - "l2scanner/ponte_config.py — [discord] do config.toml e DISCORD_TOKEN do .env, stdlib pura"
  - "l2scanner/ponte_nucleo.py — NucleoDaPonte.receber sincrono, Decisao, MensagemRecebida, ClienteDiscordEmMemoria, mensagem_de_teste"
  - "l2scanner/ponte_discord.py — o UNICO import discord do projeto; INTENCOES == 33281; Ponte(discord.Client) e main()"
  - "ponte-discord.bat — entrypoint de dois cliques que confere e RECUSA, nunca instala"
  - "PORTAO-DISCORD.txt — os 4 passos do portao humano e o aviso da armadilha de mencao"
  - "discord.py>=2.7.1,<3 declarado no requirements.txt e instalado no .venv de producao"
affects: [01-02 (validacao de arranque e pre-voo da intent), 01-03 (livro de ja-vistos, log rotativo, painel), Fase 2 (formato), Fase 3 (entrega)]

actuals:
  tokens: 17397
  tasks: 4
  commits: 4

tech-stack:
  added: ["discord.py 2.7.1 (+10 distribuicoes transitivas)"]
  patterns:
    - "Divisao em tres modulos por AMBIENTE, nao por camada: os dois que os testes importam sao stdlib pura, e so o terceiro escreve `import discord`"
    - "Async so na beirada: `on_message` normaliza e chama um metodo SINCRONO, no espirito de `Sessao.tick(frame, momento)`"
    - "Duble em memoria mora no codigo de PRODUCAO (ClienteDiscordEmMemoria), como o NotificadorEmMemoria"
    - "Injecao de identidade pos-conexao: `on_ready` -> `definir_id_da_ponte(self.user.id)` antes de qualquer log"
    - "`.bat` que CONFERE e RECUSA em vez de instalar, porque o .venv e compartilhado com o scanner em farm"

key-files:
  created:
    - l2scanner/ponte_config.py
    - l2scanner/ponte_nucleo.py
    - l2scanner/ponte_discord.py
    - ponte-discord.bat
    - PORTAO-DISCORD.txt
    - tests/test_ponte_config.py
    - tests/test_ponte_nucleo.py
    - tests/test_ponte_bat.py
  modified:
    - requirements.txt
    - config.toml
    - ENV-EXEMPLO.txt

key-decisions:
  - "`discord.py` declarado DIRETO no requirements.txt; um segundo arquivo por `-r` faria o firewall de escopo levantar AssertionError por construcao"
  - "Instalacao pelo nome e pela faixa (`pip install \"discord.py>=2.7.1,<3\"`), NUNCA `-r requirements.txt`: os pinos do scanner sao abertos e um `-r` durante o farm reescreveria cv2.pyd e as DLLs do numpy carregadas"
  - "Arquivo ou secao [discord] AUSENTE E ERRO — contraste deliberado com `ler_agenda`, porque a ponte e processo dedicado e nao acessorio (CONF-03)"
  - "`conversa_de_destino` vazia continua sendo config VALIDA: na Fase 1 a ponte so simula, e exigir o id impediria o proprio criterio 2 de ser conferido"
  - "`ponte-discord.bat` e ASCII PURO, nao cp1252 — a raiz tem os dois encodings misturados e um travessao quebraria para metade dos leitores"
  - "A intent SERVER MEMBERS fica de fora: `clean_content` ja resolve apelido de servidor via `Message.mentions`, e a segunda intent privilegiada custaria mais um clique no portao humano por nada"

patterns-established:
  - "Teste de estrutura por SUBPROCESSO: `test_importar_o_nucleo_nao_puxa_o_discord` roda `python -c` num processo limpo, porque dentro do pytest outro teste ja poderia ter importado a lib e mascarado a regressao"
  - "Varredura de linhas EXECUTAVEIS do `.bat` (descartando REM antes) para transformar 'esta janela nao instala nada' de promessa em asercao"

requirements-completed: [PONTE-02, PONTE-03, PONTE-04, CONF-01, CONF-02, OPER-01]

coverage:
  - id: D1
    description: "discord.py 2.7.1 declarado e instalado, com as 4 varreduras do firewall de escopo verdes DEPOIS da instalacao"
    requirement: "PONTE-05"
    verification:
      - kind: unit
        ref: "tests/test_firewall_escopo.py (17 passed, 1 skipped no worktree sem .venv)"
        status: pass
      - kind: other
        ref: "varredura de producao rodada a mao contra C:\\Users\\refun\\Desktop\\Lineage2-warnings\\.venv\\Lib\\site-packages: 25 distribuicoes, discord-py presente, zero banidas nas duas varreduras"
        status: pass
      - kind: other
        ref: "diff do `pip list --format=freeze` antes/depois: 10 linhas ADICIONADAS, zero linhas alteradas"
        status: pass
    human_judgment: false
  - id: D2
    description: "O nucleo aceita bot e webhook, recusa so o proprio id e os canais de fora, e a trava do proprio id chega por injecao no on_ready"
    requirement: "PONTE-04"
    verification:
      - kind: unit
        ref: "tests/test_ponte_nucleo.py (22 testes, incluindo test_depois_de_definir_id_da_ponte_o_MESMO_nucleo_passa_a_descartar)"
        status: pass
    human_judgment: false
  - id: D3
    description: "So os dois canais configurados passam; qualquer outro canal e qualquer thread sao ignorados"
    requirement: "PONTE-02"
    verification:
      - kind: unit
        ref: "tests/test_ponte_nucleo.py#TestSoOsDoisCanais"
        status: pass
    human_judgment: false
  - id: D4
    description: "Config e segredo lidos com stdlib; ausencia e erro de arranque e nenhuma mensagem carrega o valor do token"
    requirement: "CONF-01"
    verification:
      - kind: unit
        ref: "tests/test_ponte_config.py (16 testes, incluindo test_nenhuma_mensagem_de_erro_carrega_o_VALOR_do_token)"
        status: pass
      - kind: integration
        ref: "`.venv\\Scripts\\python.exe -m l2scanner.ponte_discord` sem .env: le a secao [discord] real, imprime o conserto e sai com codigo 2"
        status: pass
    human_judgment: false
  - id: D5
    description: "ponte-discord.bat sobe o modulo sem tocar __main__.py e NUNCA roda instalador de pacote"
    requirement: "OPER-01"
    verification:
      - kind: unit
        ref: "tests/test_ponte_bat.py#TestEstaJanelaNuncaMexeNoAmbienteDoScanner"
        status: pass
    human_judgment: false
  - id: D6
    description: "O usuario da dois cliques no ponte-discord.bat e ve o TEXTO REAL de uma mensagem que acabou de postar num dos dois canais"
    requirement: "PONTE-01"
    verification: []
    human_judgment: true
    rationale: "PORTAO HUMANO. Depende dos 4 passos que so o usuario pode dar (criar a aplicacao, ligar MESSAGE CONTENT, convidar o bot, informar a conversa de destino). Nenhum deles foi feito ainda. Marcar isto como automatizavel seria fabricar o verde que a fase inteira existe para nao fabricar."

duration: 28min
completed: 2026-08-28
status: complete
---

# Fase 01 Plano 01: Ponte viva — a fatia ponta a ponta Summary

**A ponte do Discord existe do segredo ao console: `discord.py` auditado e instalado sem re-resolver um unico pino do scanner, tres modulos divididos por AMBIENTE (dois stdlib puros e um so com `import discord`), 78 testes verdes no Python global — e o unico item que falta e o portao humano, que continua honestamente PENDENTE.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-08-28T13:57-03:00 (aprox., leitura do plano e do mapa de padroes)
- **Completed:** 2026-08-28T14:25-03:00
- **Tasks:** 4 de 4
- **Files modified:** 11 (8 criados, 3 modificados), 1708 insercoes, ZERO delecoes

## Accomplishments

- **A primeira dependencia de rede da historia do projeto entrou auditada e sem colateral.** `discord.py>=2.7.1,<3` declarado direto no `requirements.txt` e instalado no `.venv` de producao pelo nome, nunca por `-r`. O `pip list --format=freeze` antes e depois foi comparado linha a linha: **10 adicoes, zero alteracoes** — `numpy`, `opencv-python`, `mss`, `windows-capture` e os `winrt-*` ficaram exatamente onde estavam. As quatro varreduras do firewall de escopo estao verdes DEPOIS da instalacao, e a varredura do `.venv` de producao foi rodada a mao contra o caminho real (25 distribuicoes) porque o worktree nao tem `.venv` proprio.
- **A trava da PONTE-04 existe em PRODUCAO, nao so no teste.** O `on_ready` chama `definir_id_da_ponte(self.user.id)` ANTES de logar. Sem isso, o `main` monta o nucleo com `id_da_ponte=None` (porque `Client.user` ainda e `None` antes do `run`) e o filtro do proprio id nunca dispararia no processo de verdade — verde em todo teste que passa o id na mao. Ha dois testes fechando o par: o estado `None` de pre-conexao afirmado como legitimo, e o MESMO nucleo passando a descartar depois da injecao.
- **A divisao em tres modulos virou teste, e nao intencao.** `test_importar_o_nucleo_nao_puxa_o_discord` roda um subprocesso limpo e afirma que `discord` nao entra em `sys.modules` ao importar `ponte_nucleo` e `ponte_config`. Se um dia entrar, a suite inteira morreria na COLETA (o pytest roda no Python global, sem `discord`) — e este teste da o vermelho pelo motivo certo, com o motivo escrito.
- **O `.bat` nao instala nada, e isso e uma asercao executavel.** `tests/test_ponte_bat.py` varre as linhas EXECUTAVEIS do arquivo (descartando os `REM`, porque a propria justificativa contem as palavras procuradas) e exige que nenhuma cite o instalador ou a lista de requisitos. E a forma testavel de "dois cliques nesta janela nunca escrevem por cima do `cv2.pyd` com o scanner farmando".
- **O aviso da armadilha de mencao esta no `PORTAO-DISCORD.txt` e foi provado por mutacao a mao:** removendo o bloco, a suite fica vermelha (1 failed, 19 passed); devolvendo, volta a 20 verdes.

## Task Commits

1. **Task 1: Portao de legitimidade do pacote** — checkpoint `human-verify`, `gate="blocking-human"`. **APROVADO PELO USUARIO ANTES DA EXECUCAO** (evidencia abaixo). Sem commit proprio, de proposito: o portao nao produz artefato.
2. **Task 2: Declarar e instalar a dependencia** — `0fc57e9` (feat)
3. **Task 3: A fatia ponta a ponta** (`tdd="true"`, tracer) — `9703fec` (test, RED) -> `ab5eff1` (feat, GREEN). Sem commit de refactor: nao houve limpeza a fazer.
4. **Task 4: O `.bat` proprio e o roteiro do portao humano** — `0657e99` (feat)

Gates de TDD conferidos no `git log`: existe um `test(...)` e, depois dele, um `feat(...)`. RED foi observado de verdade — os dois arquivos de teste falharam na COLETA (`ModuleNotFoundError: No module named 'l2scanner.ponte_config'`) antes de qualquer modulo existir.

## Task 1 — a evidencia do portao de legitimidade, para a trilha de auditoria

O portao foi resolvido pelo usuario ANTES desta execucao comecar, com o pacote
identificado no PyPI por `pip install --dry-run --no-deps --report`, sem instalar
nada:

```
nome     : discord.py
versao   : 2.7.1
resumo   : A Python wrapper for the Discord API
autor    : Rapptz            <- o mantenedor legitimo
licenca  : MIT
arquivo  : discord_py-2.7.1-py3-none-any.whl
sha256   : 849dca2c63b171146f3a7f3f8acc0424...
```

Os vizinhos de nome (`discord`, `discordpy`, `discord-py`) foram nomeados ao
usuario, junto do fato de esta ser a primeira dependencia de rede do projeto.
**Resposta do usuario: "Autorizo, e o pacote certo."**

A resolucao real, medida contra o `.venv` desta maquina, bateu com a pesquisa:
11 distribuicoes, 10 novas (`typing_extensions` ja estava la), e `audioop-lts`
NAO entrou — porque o `.venv` e Python 3.12.10 e aquele marcador exige `>= 3.13`.

## Files Created/Modified

- `requirements.txt` — ganhou `discord.py>=2.7.1,<3` direto, com o comentario dizendo que ela e o CONTRATO DO PROTOCOLO (handshake, IDENTIFY, RESUME, sequencia, heartbeat, zlib, backoff, excecao de intent) e nao "mais uma dependencia"
- `l2scanner/ponte_config.py` (142 linhas) — `PonteInvalida`, `ConfigDaPonte`, `ler_config_da_ponte`, `ler_token_do_discord`. Zero import de terceiro; reusa o `ler_env` de `config.py:40`
- `l2scanner/ponte_nucleo.py` (226 linhas) — `MensagemRecebida`, `Decisao`, `Resultado`, `NucleoDaPonte`, `linha_do_console`, `ClienteDiscordEmMemoria`, `mensagem_de_teste`. Zero import de terceiro
- `l2scanner/ponte_discord.py` (213 linhas) — `INTENCOES` (== 33281), `Ponte(discord.Client)`, `normalizar`, `configurar_log`, `main`. O UNICO arquivo do projeto com `import discord`
- `config.toml` — secao `[discord]` no fim, com cabecalho comentado campo a campo e o aviso de que, ao contrario da agenda, ela NAO pode faltar
- `ENV-EXEMPLO.txt` — bloco novo ensinando onde achar o token e terminando em `DISCORD_TOKEN=`
- `ponte-discord.bat` (81 linhas) — `avisos-tvt.bat` com o titulo trocado, mais a sonda de `import discord` que RECUSA sem instalar, mais a linha de despedida
- `PORTAO-DISCORD.txt` (132 linhas) — os 4 passos e o aviso da armadilha de mencao
- `tests/test_ponte_nucleo.py` (22 testes), `tests/test_ponte_config.py` (16 testes), `tests/test_ponte_bat.py` (20 testes)

## Decisions Made

Todas as decisoes travadas do plano foram seguidas. As que exigiram julgamento no caminho:

1. **`conversa_de_destino = ""` continua sendo config valida.** O plano manda validacao minima ("chave ausente levanta nomeando a chave"), e a chave existe com valor vazio no `config.toml` versionado. Exigir valor nao-vazio agora impediria o proprio criterio 2 da fase de ser conferido — o usuario ainda nao rodou o passo 4. Ha teste afirmando isso com o motivo escrito, para que o `01-02-PLAN.md` nao "conserte" por engano.
2. **`configurar_log` foi COPIADO, nao importado.** Como manda a restricao dura: importar de `__main__.py` amarraria a ponte ao modulo de 2047 linhas que outro workstream esta editando. A copia e so a metade de console; o arquivo rotativo e o OPER-02, do `01-03-PLAN.md`.
3. **Nada de pre-voo de intent, livro de ja-vistos, log rotativo ou painel.** Sao explicitamente `01-02` e `01-03`. O `Decisao` enum deixou espaco mas NAO inventou membros: um membro de enum sem codigo que o produza e caminho morto que parece coberto.

## Deviations from Plan

### 1. [Rule 1 - Bug] Um teste meu afirmava a coisa errada

- **Found during:** Task 3 (fase GREEN)
- **Issue:** `test_config_ausente_e_erro_e_nao_um_padrao_silencioso` passava `tmp_path / "nao-existe.toml"` e exigia a string `"config.toml"` na mensagem. A implementacao (correta) nomeia o arquivo que ela procurou, entao a mensagem dizia `nao-existe.toml`. O teste estava errado, nao o codigo.
- **Fix:** o teste agora aponta para `tmp_path / "config.toml"` (que e o caso real: o `config.toml` sumiu) e passou a exigir tambem `"[discord]"` na mensagem, o que e a asercao que ele queria fazer desde o comeco.
- **Verification:** 38 verdes em `test_ponte_nucleo.py` + `test_ponte_config.py`
- **Committed in:** `ab5eff1`

### 2. [Rule 1 - Bug] O aviso da armadilha quebrado em duas linhas

- **Found during:** Task 4
- **Issue:** `test_o_roteiro_avisa_para_NAO_mencionar_o_bot` pina o literal `MESMO COM A INTENT DESLIGADA`, e a frase estava quebrada entre duas linhas no `PORTAO-DISCORD.txt`. Vermelho legitimo: o teste existe para garantir que o aviso esteja LA, e um literal partido derrota qualquer varredura futura.
- **Fix:** a frase virou uma linha propria, o que de quebra a destaca mais no arquivo que o usuario vai ler.
- **Verification:** 20 verdes; e a mutacao (remover o bloco inteiro) reproduz o vermelho.
- **Committed in:** `0657e99`

### 3. [Rule 2 - Correcao] O `.bat` e ASCII PURO, nao cp1252

- **Found during:** Task 4
- **Issue:** o plano diz "o arquivo esta em cp1252, como os outros da raiz". **Medido, isso nao e verdade da raiz inteira:** `calibrar-mercado.bat` e cp1252 (1 byte fora do ASCII, e o arquivo nao decodifica como utf-8), mas `avisos-tvt.bat` (12 bytes) e `vigiar-party.bat` (9 bytes) sao utf-8 validos. Escrever um travessao no arquivo novo o faria aparecer certo para um leitor e quebrado para o outro, dependendo do editor e da pagina de codigo do console.
- **Fix:** o `ponte-discord.bat` nao tem um byte fora do ASCII. Assim ele decodifica identico em cp1252 e em utf-8, e o teste pode le-lo com `cp1252` (como o plano manda e como o `test_calibrar_mercado_bat.py` faz) com zero ambiguidade. Ha um teste (`test_o_bat_e_ascii_puro`) pinando a propriedade com o motivo medido na docstring.
- **Verification:** `tests/test_ponte_bat.py::TestOsArquivosExistem::test_o_bat_e_ascii_puro`
- **Committed in:** `0657e99`

### 4. [Rule 2 - Cobertura] Dois testes a mais que o plano nao pediu

- **Found during:** Tasks 3 e 4
- **Issue:** a restricao dura numero 5 ("a divisao em tres modulos e load-bearing") e a restricao numero 3 ("o `.bat` nunca roda instalador") sao invariantes que nada no repositorio guardava.
- **Fix:** `test_importar_o_nucleo_nao_puxa_o_discord` (subprocesso limpo) e `test_o_comentario_que_explica_a_proibicao_continua_no_lugar`. Ambos sao cobertura, nao escopo novo.
- **Committed in:** `ab5eff1`, `0657e99`

---

**Total deviations:** 4 auto-corrigidas (2x Rule 1, 2x Rule 2)
**Impact on plan:** nenhum desvio de escopo. Duas correcoes de testes meus, uma correcao de um fato do plano que a medicao contradisse (encoding da raiz), e duas asercoes a mais guardando restricoes duras que ja existiam.

## Issues Encountered

**O worktree nao tem `.venv` proprio.** O `.venv` de producao mora na raiz do
checkout principal (`C:\Users\refun\Desktop\Lineage2-warnings\.venv`), e um
worktree do git tem arvore propria. Consequencias, todas registradas em vez de
contornadas:

1. A instalacao foi feita no `.venv` REAL, que e exatamente o que o plano pede
   ("instale no `.venv` de producao") — o `.venv` e gitignorado e compartilhado
   por desenho, e nao pertence a nenhum branch.
2. `tests/test_firewall_escopo.py::test_o_venv_de_producao_nao_tem_biblioteca_de_input`
   **PULA** quando rodado do worktree, porque procura `.venv` ao lado do arquivo
   de teste. Esse skip e documentado pelo proprio teste ("num clone limpo ou em
   CI o ambiente de producao ainda nao foi criado"). Para nao aceitar um skip
   onde o roadmap manda VER passar, as varreduras 3 e 4 foram executadas a mao
   chamando as MESMAS funcoes do modulo de teste com o caminho real: 25
   distribuicoes, `discord-py` presente, zero banidas nas duas. Resultado
   observado, nao suposto.
3. Os comandos que carregam `l2scanner.ponte_discord` usam o python do `.venv`
   por caminho absoluto com o cwd no worktree, para que o `discord` venha do
   `.venv` e o `l2scanner` venha do codigo novo.

**Nada mais.** Nenhum teste existente regrediu: a suite inteira e **1438 passed,
8 skipped**.

## Verificacao — o que esta verde e o que esta PENDENTE

| # | Item da `<verification>` do plano | Estado |
|---|---|---|
| 1 | `pytest tests/test_firewall_escopo.py tests/test_ponte_nucleo.py tests/test_ponte_config.py tests/test_ponte_bat.py -q` no Python GLOBAL | **VERDE** — 75 passed, 1 skipped (o skip e o do `.venv`, item 2 dos Issues) |
| 2 | `pytest -q` (suite inteira) nao regride | **VERDE** — 1438 passed, 8 skipped |
| 3 | `.venv/Scripts/python.exe -c "import l2scanner.ponte_discord"` carrega | **VERDE** — carrega e `INTENCOES.value == 33281` |
| 4 | `git diff --stat l2scanner/notificador.py l2scanner/__main__.py` sai vazio | **VERDE** — saida vazia, e os dois arquivos nao aparecem no `git diff --stat` dos 4 commits |
| 5 | Dois cliques no `.bat` mostram a conexao e o texto real | **PENDENTE — PORTAO HUMANO** |

E o `done` de cada tarefa:

| Tarefa | `done` | Estado |
|---|---|---|
| 2 | `discord.py` direto no requirements; `.venv` recebeu SO esse pacote; firewall verde depois | **VERDE**, com o diff do `pip list` como prova de que nenhum pino foi re-resolvido |
| 3 | Tres modulos existem e importam; testes passam no Python global SEM `discord`; `.venv` carrega o modulo e `INTENCOES == 33281` | **VERDE** |
| 4 | `.bat` existe, sonda so `import discord` e recusa sem instalar; roteiro com os 4 passos e o aviso; teste falharia se o aviso sumisse | **VERDE**, com a mutacao executada a mao |

## O que NAO foi conferido, e por que — PORTAO HUMANO

**O criterio 2 da Fase 1 continua PENDENTE e nao pode ser marcado verde.** Os
4 passos do `PORTAO-DISCORD.txt` nao foram dados: nao existe aplicacao criada no
Discord, a intent MESSAGE CONTENT nao esta ligada, o bot nao foi convidado e nao
ha `conversation_id` de destino. Nao existe `.env` nesta arvore.

Em consequencia, nada disto foi observado e nada disto esta sendo afirmado:

- a ponte conectando de verdade no servidor XM Games;
- o texto REAL de uma mensagem aparecendo no console;
- o comportamento de uma mensagem que chega VAZIA com a intent desligada;
- o comportamento do `ponte-discord.bat` executado de verdade ponta a ponta (a
  guarda do `.venv` dispararia no worktree, e o `pause` seguraria a janela).

O que FOI observado sem o portao, e que e o mais perto honesto que da para
chegar: o modulo carrega no `.venv` com as intents certas, e
`python -m l2scanner.ponte_discord` sem `.env` le a secao `[discord]` de verdade
do `config.toml`, imprime a linha de conserto nomeando `DISCORD_TOKEN` e sai com
codigo **2** — sem traceback cru.

## Exigencias — duas SEGURADAS de proposito

O `requirements` do plano lista oito. O `requirements-completed` deste sumario
lista **seis**. As duas que ficaram de fora nao ficaram por esquecimento:

- **PONTE-01** ("a ponte conecta no Discord com um token de bot proprio") — o
  codigo esta pronto e o caminho de erro foi exercitado, mas **conexao nenhuma
  aconteceu**. Marcar PONTE-01 como cumprida seria exatamente o verde fabricado
  que esta fase inteira existe para nao fabricar. Ela fecha no portao humano.
- **PONTE-05** ("a ponte roda como processo separado; subir, cair ou reiniciar
  um nao afeta o outro") — a metade estrutural esta feita e provada (modulo,
  entrypoint e `.bat` proprios; `__main__.py` e `notificador.py` byte-identicos;
  o `.bat` nao roda instalador contra o `.venv` compartilhado). A metade
  observavel — os dois processos vivos lado a lado sem se sentirem — exige a
  ponte conectada, ou seja, o mesmo portao.

As duas voltam a mesa assim que o criterio 2 for conferido.

## User Setup Required

**Sim — e e o bloqueio da fase.** Ver `PORTAO-DISCORD.txt` na raiz:

1. Criar a aplicacao em `discord.com/developers/applications`, adicionar um Bot,
   colar o token na linha `DISCORD_TOKEN=` do `.env`.
2. Ligar **MESSAGE CONTENT INTENT** em "Privileged Gateway Intents" e salvar.
3. Convidar o bot para o XM Games com `View Channel` + `Read Message History`
   nos dois canais.
4. Rodar `.venv\Scripts\python.exe tools\check_whatsapp.py conversas` e escrever
   o id em `conversa_de_destino` no `config.toml`.

**Ao testar: poste `teste da ponte 1` SEM arroba nenhuma.** Uma mensagem que
menciona o bot chega com texto MESMO COM A INTENT DESLIGADA — testar com arroba
produz um verde que nao prova nada.

## Known Stubs

Nenhum. Todo caminho escrito nesta fatia e executado por teste ou pelo arranque
real. O que nao existe (pre-voo da intent, livro de ja-vistos, log rotativo,
painel de status, formato, entrega) nao esta esbocado em lugar nenhum: nao ha
funcao vazia, nao ha `TODO`, e o `Decisao` enum tem exatamente os tres membros
que o codigo produz.

## Next Phase Readiness

**Pronto para o `01-02-PLAN.md`** (validacao de arranque, pre-voo deterministico
da intent, heuristica de runtime, modo `--conferir`). Ele encontra:

- `PonteInvalida` e `ler_config_da_ponte` com validacao MINIMA, exatamente no
  ponto onde o rigor completo deve entrar (tipo, faixa, a armadilha do `bool`
  ser subclasse de `int`, o guarda de higiene da conversa de destino);
- `Ponte(discord.Client)` sem `setup_hook` — o gancho do pre-voo esta livre;
- `main()` ja tratando `PrivilegedIntentsRequired` e `LoginFailure`, pronto para
  ganhar `IntentDeConteudoDesligada` ao lado.

**Pronto para o `01-03-PLAN.md`** (livro de ja-vistos, log rotativo, painel):

- `Decisao` com espaco declarado para os membros novos;
- `configurar_log()` isolado numa funcao propria, para virar o rotativo do
  OPER-02 sem tocar em mais nada;
- `Ponte.ultima_vista` ja existe, alimentando o painel do OPER-03;
- `ponte.run(token, log_handler=None)` ja no lugar, que e a pre-condicao do
  OPER-02 (sem ele a biblioteca instala um `StreamHandler` proprio).

**Bloqueio para a Fase 2:** o roadmap diz que ela nao deve ser planejada em
detalhe antes do criterio 2 estar conferido. Ele nao esta. Formatar texto que
nunca se provou existir e trabalho em cima de suposicao.

## Self-Check: PASSED

Os 11 arquivos criados/modificados e o proprio sumario existem em disco; os 4
commits (`0fc57e9`, `9703fec`, `ab5eff1`, `0657e99`) existem no `git log`.

---
*Phase: 01-ponte-viva-conexao-provada-e-texto-real*
*Completed: 2026-08-28*
