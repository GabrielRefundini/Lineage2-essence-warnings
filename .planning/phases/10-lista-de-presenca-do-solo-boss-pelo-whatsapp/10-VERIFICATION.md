---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
verified: 2026-08-26T00:00:00Z
status: human_needed
score: 40/40 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Rodar o scanner (ou `--so-agenda`) com `.env` e `[[membro]]` reais e conferir no celular os 7 itens do ciclo completo (chamada 1h50, .join, nick no grupo, .join repetido, .leave, fechamento com e sem lista, .corrigir recusado)"
    expected: "Os 7 itens do bloco `<human-check>` da Tarefa 2 do 10-05-PLAN.md, reproduzidos verbatim em 10-UAT.md"
    why_human: "A costura com o Chatwoot real e a ponte Baileys nao existe offline. `__main__.py` tem 19-20% de cobertura e e onde os 3 warnings do code review moravam."
  - test: "Ler o bloco `[[membro]]` comentado do config.toml como se fosse a primeira vez"
    expected: "Um nao-programador consegue preencher nick e telefone sem ajuda (10-01 D7)"
    why_human: "Legibilidade para leigo nao e verificavel por grep"
  - test: "Ler o texto da chamada como se ele chegasse no grupo do WhatsApp"
    expected: "Pergunta clara, horario visivel, instrucao de onde responder (10-02 D7)"
    why_human: "Qualidade de redacao e julgamento humano"
  - test: "Ler as mensagens de `.join`/`.leave` do ponto de vista de um party-mate que so ve o WhatsApp"
    expected: "Claras e uteis nos 6 desfechos (entrou / ja estava / erro de disco / saiu / nunca entrou / boss ja comecou) (10-03 D9)"
    why_human: "Qualidade de redacao e julgamento humano"
  - test: "Um party-mate manda `.join` no privado do bot"
    expected: "Ele ve chegar uma resposta util no privado enquanto o grupo ve o nick entrar na lista (10-03b D7)"
    why_human: "Depende do Chatwoot real e de um segundo telefone"
  - test: "Ler a lista fechada no grupo pensando nas doze ocorrencias por dia"
    expected: "A redacao le bem e nao vira ruido (10-04 D8)"
    why_human: "Percepcao de volume/ruido e julgamento humano"
---

# Phase 10: Lista de presenca do Solo Boss pelo WhatsApp — Verification Report

**Phase Goal:** A party sabe com uma hora e cinquenta de antecedencia quem vai no proximo Solo Boss, sem ninguem perguntar de boca — o scanner pergunta no grupo, cada um responde `.join` no privado, e a lista se fecha sozinha no horario.

**Verified:** 2026-08-26
**Status:** human_needed
**Re-verification:** Nao — verificacao inicial

---

## Goal Achievement

### Success Criteria do ROADMAP

| # | Criterio | Status | Evidencia |
|---|---|---|---|
| 1 | Chamada 1h50 antes chega no grupo com o horario; o aviso de 10 min continua existindo | VERIFIED | Probe executado: `avisos_devidos(20:10)` devolve exatamente 1 `CHAMADA` com `alvo=22:00`, chave `2026-08-26_solo-boss-2200_chamada`; `avisos_devidos(21:50)` continua devolvendo o `ANTES` do Solo Boss. Texto: "Solo Boss as 22:00. Quem vai? Mande .join no PRIVADO do bot...". TvT sem `chamar_minutos_antes` nao ganha chamada nenhuma. |
| 2 | `.join` no privado -> grupo recebe o NICK (nao o nome do contato); `.join` repetido nao vira segunda mensagem no grupo | VERIFIED | Probe e2e por `atender_comandos` com despachante falso: 1o `.join` -> 2 despachos (`conversa=7` "Anotado...", `conversa=None` "J4guar vai no Solo Boss das 20:00."); 2o `.join` -> 1 despacho so na origem. `comandos_novos` devolve `nick='J4guar'` (do `[[membro]]`) e `autor='Ze do Whats'` (do `sender.name`) — os dois campos existem e nao se confundem. |
| 3 | `.leave` sai da lista e o grupo sabe; `.leave` de quem nunca joinou responde isso e nao anuncia | VERIFIED | Probe: `responder_leave` de quem joinou -> `grupo="J4guar saiu da lista..."`; de quem nao joinou -> `grupo=None`, `privado="Voce nao estava na lista..."`. `.leave` as 20:01 de quem estava na lista fechada -> `grupo=None`, "O Solo Boss das 20:00 ja comecou e a lista fechou." (PRES-13) |
| 4 | Membro da party da `.join` sem ganhar `.cancelar`/`.loot-<nick>`/`.corrigir`; autorizacao em DOIS niveis; descoberta pela etiqueta `CP` ja existente | VERIFIED | Probe sobre o enum: membro alcanca os 2 de `COMANDOS_DE_MEMBRO` e e recusado nos **10 restantes derivados de `set(Comando) - COMANDOS_DE_MEMBRO`** (ajuda, cancelar_silencio, loot_atribuir, loot_cancelar, loot_consulta, loot_corrigir, loot_designar, party, solo, status). Dono alcanca os 12. E2e: `.corrigir-J4guar` de membro produz ZERO despacho. `LeitorDeComandos(etiqueta=)` intocado. |
| 5 | No horario a lista fecha, o grupo recebe quem confirmou, e a lista fechada alimenta o revezamento de loot | VERIFIED | Probe: lista vazia -> `fechar_ocorrencias` devolve `[]` e NAO cria `fechado_*`; com 2 joins -> 1 `Fechamento(nicks=('j4guar','tiomad'))`; 2a instancia sobre a mesma pasta -> `[]`. Texto: "Solo Boss das 20:00 comecando. Confirmaram: J4guar, TioMad." (grafia do config.toml). `sugerir_a_vez(registro, frozenset(fechamento.nicks))` escolhe entre os presentes. |
| 6 | Tudo demonstravel sem jogo e sem rede; tempo por parametro; etiqueta e mapa por dado; corrida das duas instancias com teste proprio | VERIFIED | Suite inteira offline: `python -m pytest tests/ -q` -> **1051 passed, 2 skipped** (os 2 skips sao de OCR, pre-existentes). Todos os probes desta verificacao rodaram com o jogo fechado e sem rede. Testes de corrida com **16 threads** em `tests/test_agenda.py` (`test_competicao_de_verdade_com_threads` para `marcar`, e o irmao para `entrar`) — executados, 3 passed. |

**Score:** 6/6 criterios do ROADMAP verificados.

### Must-haves dos seis planos

| Plano | Truth | Status | Evidencia |
|---|---|---|---|
| 10-01 | Telefone de `[[membro]]` atravessa as 5 travas no `.join` | VERIFIED | `comandos_novos` com `message_type=0` devolve `JOIN` para o membro |
| 10-01 | Recusado nos 10 demais comandos | VERIFIED | Lista derivada do enum, probe acima |
| 10-01 | Nivel de dono continua alcancando TODOS — aditivo | VERIFIED | `autorizado_para` avalia `autor_autorizado` PRIMEIRO; probe sobre `set(Comando)` |
| 10-01 | Nick vem do mapa, nunca de `sender.name` | VERIFIED | `membro_do_remetente` resolvido UMA vez e usado pela trava e pelo `nick` |
| 10-01 | Colisao de 8 digitos vira aviso alto no arranque | VERIFIED (**e mais**) | Par membro×membro avisa e sobe; par **dono×membro RECUSA A SUBIR** (`ConfiguracaoPerigosa`, `main()` -> `return 2`) — ver CR-01 abaixo |
| 10-01 | `config.toml` do repositorio sem telefone nenhum | VERIFIED | `git diff` do `config.toml`: so exemplos comentados |
| 10-02 | Chamada a 1h50 com o horario do proximo boss | VERIFIED | Probe SC1 |
| 10-02 | Aviso de 10 min intacto, com a linha `Loot:` | VERIFIED | `texto_do_aviso` inalterado no ramo `ANTES`; probe SC1 |
| 10-02 | TvT e Prime sem chamada (opt-in) | VERIFIED | `chamar_minutos_antes <= 0` -> `continue`; probe |
| 10-02 | Agenda nunca escreve "Solo Boss" no codigo | VERIFIED | Varredura do fonte de `agenda.py` sem comentarios e sem docstrings: zero ocorrencias |
| 10-02 | Chave duravel da chamada distinta, marcadores antigos preservados | VERIFIED | Chave observada `..._chamada` vs `..._antes`/`..._agora` |
| 10-03 | `.join` poe o nick na lista e o grupo recebe esse NICK | VERIFIED | Probe e2e |
| 10-03 | A resposta diz QUAL horario pegou | VERIFIED | `.join` as 19:00 -> "das 20:00"; as 20:10 -> "das 22:00" |
| 10-03 | `.join` repetido so no privado | VERIFIED | `grupo is None`, "voce ja esta na lista" |
| 10-03 | Duas redacoes DIFERENTES | VERIFIED | `privado != grupo` no probe |
| 10-03 | `.leave` tira e anuncia; de quem nao joinou nao anuncia | VERIFIED | Probe SC3 |
| 10-03 | `.leave` depois do fechamento e recusado | VERIFIED | Probe as 20:01 |
| 10-03 | 16 threads no mesmo `.join` -> 1 confirmacao | VERIFIED | `tests/test_agenda.py` executado (3 passed) |
| 10-03 | Marcador de 4 dias podado; o de hoje sobrevive | VERIFIED | Probe direto em `podar`: apagou 2 (`presenca_` e `fechado_` velhos), sobreviveu `presenca_2026-08-26_...` |
| 10-03b | `.join` de membro -> DOIS despachos com textos DIFERENTES | VERIFIED | Probe e2e por `atender_comandos` |
| 10-03b | `.join` repetido -> UM despacho na origem | VERIFIED | Probe e2e |
| 10-03b | Os 8 ramos antigos mantem o destino que tinham | VERIFIED | `.status` -> 1 na origem; `.cancelar` -> 2 com o MESMO texto; mais `TestDestinoDosComandosAntigos` (10 casos) |
| 10-03b | `comandos_novos` recebe `membros` nas DUAS chamadas | VERIFIED | Teste AST parametrizado sobre `laco_principal` e `laco_da_agenda` |
| 10-04 | No horario a lista fecha e o grupo recebe quem confirmou | VERIFIED | Probe + `Sessao._processar_agenda` despacha `Categoria.SEMPRE` |
| 10-04 | Zero confirmacoes -> ZERO mensagem | VERIFIED | `fechar_ocorrencias` devolve `[]`; ambos os chamadores so logam/despacham dentro do laco |
| 10-04 | Fechamento independe de `avisar_no_horario` | VERIFIED | `ocorrencias_na_janela` filtra por `chamar_minutos_antes > 0` apenas; probe com `avisar_no_horario=False` |
| 10-04 | Duas instancias -> o grupo recebe UMA vez | VERIFIED | Segunda `RegistroEmDisco` sobre a mesma pasta devolve `[]` |
| 10-04 | Grafia do `config.toml`, nao a caixa do slug | VERIFIED | "Confirmaram: J4guar, TioMad." a partir de `presenca_..._j4guar` |
| 10-04 | Fechamento tambem em `--so-agenda` | VERIFIED | `_fechar_listas_de_presenca` testada isoladamente + teste AST prova a chamada dentro de `laco_da_agenda` |
| 10-05 | A vez e SUGERIDA entre quem estava na lista fechada | VERIFIED | `sugerir_a_vez(rl, {'J4guar','Kaus'})` -> `('j4guar', 0)` |
| 10-05 | `.loot-<nick>` de quem nao joinou GRAVA e so acrescenta aviso | VERIFIED | Probe: gravou (`nick_kaus`, `proximo.json`) **e** respondeu "(Kaus nao esta na lista de presenca deste boss, mas anotei.)" |
| 10-05 | A fase nao cria tipo de arquivo novo em `.loot/` | VERIFIED | `git diff` de `loot.py`: nenhuma escrita nova; probe confirma so os tipos da Fase 8 |
| 10-05 | `loot.py` sem importar `comandos`, `sessao` ou `presenca` | VERIFIED | AST dos imports reais: `['__future__','agenda','dataclasses','datetime','json','os','pathlib','re']` |
| 10-05 | Sugestao deterministica | VERIFIED | Duas chamadas identicas -> mesmo resultado; desempate em 3 niveis |

**Score total:** 40/40 (6 do ROADMAP + 34 dos planos).

---

## Verificacao dirigida aos seis pontos load-bearing

### 1. Autorizacao ADITIVA, com a recusa DERIVADA do enum — VERIFIED, e o portao MORDE

`COMANDOS_DE_MEMBRO` e uma lista de **inclusao** (`frozenset({JOIN, LEAVE})`), e o teste deriva a recusa como `set(Comando) - COMANDOS_DE_MEMBRO`. Testado por mutacao, com reversao limpa depois:

| Mutacao aplicada | Resultado |
|---|---|
| `COMANDOS_DE_MEMBRO` alargado com `LOOT_CORRIGIR` | `test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele` FALHOU (guarda contra prova vazia disparou primeiro) |
| `Comando.APAGAR_TUDO` novo, sem entrar em `COMANDOS_DE_MEMBRO` | **7 testes falharam** — o comando novo nasce recusado E forca a declaracao da sintaxe/ajuda |

Ordem confirmada em `autorizado_para`: `autor_autorizado` (dono) primeiro e retorna `True` para TODO comando; so depois o nivel de membro, restrito a `COMANDOS_DE_MEMBRO`.

### 2. Zero joins -> zero mensagens; fechamento independe de `avisar_no_horario` — VERIFIED

`fechar_ocorrencias` le `presentes` ANTES de `fechar`, entao lista vazia nem toca no disco (confirmado: nenhum `fechado_*` criado). `ocorrencias_na_janela` filtra por `chamar_minutos_antes > 0` — `avisar_no_horario` nao aparece em nenhum ponto do caminho de fechamento. O probe rodou com `avisar_no_horario=False`, que e o estado real do Solo Boss no `config.toml`.

### 3. `podar` alcanca todo prefixo conhecido; prefixo desconhecido fica em paz — VERIFIED

`_PREFIXOS_CONHECIDOS = (cancelado_, presenca_, fechado_)`. Probe: apagou o `presenca_` e o `fechado_` de 6 dias atras, preservou o `presenca_` de hoje e **preservou `comando_98765`** (prefixo sem data -> `ValueError` -> `continue`).

### 4. Os portoes de AST existem E MORDEM — VERIFIED por mutacao

| Mutacao aplicada | Portao | Resultado |
|---|---|---|
| `from . import presenca` em `loot.py` | `test_loot_nunca_importa_presenca` | FALHOU corretamente |
| `_MUTANTE = datetime.now()` em `agenda.py` | `test_nenhum_now_de_datetime_na_arvore[agenda.py]` | FALHOU: "agenda.py tem relogio proprio: ['datetime.now']" |

Ambas revertidas; `git status` de `l2scanner/` limpo. Os portoes tambem carregam guardas contra prova vazia (`test_presenca_importa_mesmo_de_agenda_e_de_loot`, `test_a_prova_pega_de_verdade_um_relogio_proprio`).

### 5. `sugerir_a_vez` e somente-leitura contra `.loot/` — VERIFIED

Listagem do diretorio antes e depois da chamada: **identica**. O `git diff` de `loot.py` nao introduz nenhuma escrita — `dono_do_loot` e `sugerir_a_vez` so leem (`registro.registros()`, `registro.resumo()`).

### 6. Colisao dono×membro RECUSA A SUBIR (CR-01) — VERIFIED

Probe com dono `+5544999998888` (DDD 44) e membro `+5511999998888` (DDD 11), mesmos 8 finais:

- `colisoes_de_telefone` -> 1 par com `escala_privilegio=True`
- A escalada e **real**: `autorizado_para(LOOT_CORRIGIR, membro, ...)` -> `True`
- `montar_leitor_de_comandos` levanta `ConfiguracaoPerigosa`; `main()` captura nos dois lacos e devolve `2`

Verificado tambem que nao ha falso positivo: o **mesmo numero escrito de duas formas** (com/sem o 9, com/sem +55) nao e colisao (`_forma_canonica` + `_mesma_pessoa`), e par membro×membro apenas avisa e o scanner sobe.

---

## Key Link Verification

| De | Para | Via | Status |
|---|---|---|---|
| `config.toml [[membro]]` | `autorizado_para` | `ler_membros` -> `LeitorDeComandos.membros` -> `comandos_novos(membros=)` | WIRED (probe e2e com `config.toml` real em tmp) |
| `config.toml chamar_minutos_antes` | `texto_do_aviso` | `_evento_de_dict` -> `EventoAgendado` -> `avisos_devidos` | WIRED |
| `MensagemDeComando.nick` | arquivo `presenca_*` | `responder_join` -> `apelido(nick)` | WIRED |
| `RespostaDePresenca(privado, grupo)` | `despachante.despachar` | bloco unico de despacho em `atender_comandos` | WIRED (2 destinos observados) |
| `Sessao._processar_agenda` | grupo | `fechar_e_narrar` -> `RegistroEmDisco.fechar` -> `_despachar(Categoria.SEMPRE)` | WIRED |
| `laco_da_agenda` | grupo | `_fechar_listas_de_presenca` | WIRED (teste AST) |
| `RegistroEmDisco.presentes` | `loot.sugerir_a_vez` | parametro, na borda (`fechar_e_narrar`) | WIRED — `loot` nao importa `presenca` |
| `responder_designacao(presenca=)` | sufixo consultivo | `presenca.presentes(chave)`, depois de gravar | WIRED, sem `return` de recusa |

---

## Behavioral Spot-Checks

| Comportamento | Comando | Resultado | Status |
|---|---|---|---|
| Suite completa offline | `python -m pytest tests/ -q` | 1051 passed, 2 skipped (25s) | PASS |
| Corrida de 16 threads | `pytest tests/test_agenda.py -k "competicao or entrar"` | 3 passed | PASS |
| Fechamento e despacho | `pytest tests/test_presenca.py tests/test_sessao.py -k "Fechamento or Presenca or Destino or Join or Leave"` | 154 passed | PASS |
| Tripwire do `.help` | `pytest tests/test_comandos.py -k "ajuda"` | 13 passed | PASS |
| Probe dos 6 SC (script proprio) | `python probe10.py` | 29/29 checks (1 falha inicial era bug do proprio probe: `message_type` como texto em vez de `0`) | PASS |
| Probe do e2e de despacho | `python probe_e2e.py` | 5/5 | PASS |
| Probe da colisao CR-01 | `python probe_colisao2.py` | recusou a subir | PASS |
| Probe do PRES-14 | `python probe_pres14.py` | grava e avisa | PASS |
| Lint | `python -m ruff check l2scanner/` | 2 `E741` pre-existentes de `visao.py`, zero novos | PASS |

---

## Requirements Coverage

| Req | Plano | Status | Evidencia |
|---|---|---|---|
| PRES-01 | 10-02 | SATISFIED | Probe SC1 |
| PRES-02 | 10-02 | SATISFIED | `chamar_minutos_antes <= 0` desliga; TvT sem chamada |
| PRES-03 | 10-01 | SATISFIED | 10 comandos recusados, derivados do enum |
| PRES-04 | 10-01 | SATISFIED | Dono alcanca os 12 |
| PRES-05 | 10-03/03b | SATISFIED | Probe e2e, nick do `[[membro]]` |
| PRES-06 | 10-03/03b | SATISFIED | 1 despacho na origem |
| PRES-07 | 10-03 | SATISFIED | `.join` as 19:00 -> "das 20:00" |
| PRES-08 | 10-03/03b | SATISFIED | Probe SC3 |
| PRES-09 | 10-03/03b | SATISFIED | `privado != grupo` |
| PRES-10 | 10-03 | SATISFIED | `O_CREAT\|O_EXCL`, 16 threads -> 1 |
| PRES-11 | 10-03 | SATISFIED | Probe de `podar` |
| PRES-12 | 10-04 | SATISFIED | Probe de fechamento vazio/cheio |
| PRES-13 | 10-03 | SATISFIED | `.leave` as 20:01 recusado |
| PRES-14 | 10-05 | SATISFIED | Grava e avisa, nunca recusa |
| PRES-15 | 10-03/05 | SATISFIED | Suite inteira offline; 16 threads |

**Orfaos:** nenhum. Os 15 PRES-* do ROADMAP aparecem no campo `requirements` de pelo menos um plano.

---

## Test Quality Audit

| Item | Resultado |
|---|---|
| Testes desabilitados ligados a requisito | **0** — nenhum `skip`/`xfail` nos 5 arquivos da fase; os 2 skips da suite sao de OCR, pre-existentes |
| Testes circulares | **0** — nenhum script gera valor esperado rodando o sistema sob teste; as fixtures sao literais e datas fixas |
| Guardas contra prova vazia | **presentes em 3 lugares** — `test_presenca_importa_mesmo_de_agenda_e_de_loot`, `test_a_prova_pega_de_verdade_um_relogio_proprio`, e o `assert {LOOT_CORRIGIR, LOOT_ATRIBUIR} <= recusados` do tripwire da fronteira |
| Forca das assercoes | Nivel **valor** e **comportamental** — a tabela de destinos afirma `(conversa, texto)` por ramo; o fechamento afirma a string inteira; a fronteira itera o enum |
| Portoes testados por mutacao | **4 de 4 morderam** (ver secao 4 acima) |

**Blockers do audit de testes:** nenhum.

---

## Anti-Patterns Found

| Arquivo | Linha | Padrao | Severidade | Impacto |
|---|---|---|---|---|
| — | — | Nenhum marcador `TODO`/`FIXME`/`TBD`/`XXX`/`HACK`/`PLACEHOLDER` nos arquivos da fase | — | Os hits de grep sao a palavra portuguesa "TODO/TODOS" em prosa e `TODOS_OS_DIAS` |
| — | — | Nenhum `return {}`/`return []`/`pass` como implementacao vazia | — | Os `pass` sao `except OSError: pass`, deliberados |

---

## Observacoes nao bloqueantes (WARNING / INFO)

**W-1 — o portao de prefixos nao e derivado (`agenda.py`).**
`_PREFIXOS_CONHECIDOS` alcanca hoje os tres prefixos existentes e o comentario avisa que "um prefixo novo tem que entrar AQUI, ou nasce imortal em silencio". Mas o teste (`TestPodaAlcancaTodosOsPrefixos`) usa um `parametrize` **escrito a mao** — a mesma coisa que `COMANDOS_DE_MEMBRO` conscientemente evitou. Um `PREFIXO_X` futuro nasceria imortal sem quebrar teste nenhum.
*Recomendacao (~5 linhas, cabe num `/gsd-quick`):* derivar o conjunto — `{v for n, v in vars(agenda).items() if n.startswith("PREFIXO_")} == set(_PREFIXOS_CONHECIDOS)`. Verifiquei que a afirmacao passa hoje e morderia amanha.

**W-2 — o portao de direcao de import cobre `loot -> presenca`, mas nao `loot -> comandos/sessao`.**
O must-have do 10-05 diz "`loot.py` continua sem importar `comandos`, `sessao` ou `presenca`". Confirmei por AST que **isso e verdade agora** (imports reais: `agenda` + stdlib). Mas `test_loot_nunca_importa_presenca` so afirma `presenca`. A regra da Fase 8 sobre `comandos`/`sessao` segue sendo politica escrita em docstring, nao estrutura.
*Recomendacao:* trocar a assercao por `assert not ({"comandos","sessao","presenca","__main__"} & importados)` — uma linha.

**I-1 — janela de fechamento de 5 minutos.**
`ocorrencias_na_janela` usa `TOLERANCIA_MINUTOS`. Um scanner fora do ar por mais de 5 minutos em cima do horario do boss nunca fecha aquela lista, e a mensagem simplesmente nao sai (os marcadores morrem na poda de 3 dias). E a mesma tolerancia que `avisos_devidos` ja usa desde a Fase 6, entao o comportamento e coerente com o projeto — registrado como fato, nao como defeito.

**I-2 — a fronteira de dois niveis fica inerte com `CHATWOOT_TELEFONES_COMANDO` vazia.**
`autor_autorizado([])` devolve `True` para qualquer remetente, entao todo mundo alcanca `.corrigir`/`.pegou`. Isso e compatibilidade pre-existente, esta **corretamente condicionado** na mensagem de arranque (WR-03: com a variavel vazia o log e `warning` e diz "os [[membro]] NAO estao contidos"), e esta escrito em ATENCAO no `config.toml`. Nao e gap.

**I-3 — `deferred-items.md`:** o `F401` pre-existente em `tests/test_sessao.py` continua la (confirmado por `ruff check tests/`), corretamente registrado como pre-existente e fora do escopo.

---

## Code Review — disposicao conferida

`10-REVIEW.md` declara 13 achados (2 CRITICAL, 11 WARNING), todos corrigidos, zero recusados. Conferi os dois criticos no codigo, nao no relatorio:

- **CR-01** (escalada de privilegio silenciosa por colisao de sufixo): confirmado por probe — `ConfiguracaoPerigosa` levantada, `main()` devolve `2`. Alem disso `_mesma_pessoa` agora exige **igualdade da forma canonica**, e nao parentesco de sufixo, que era a supressao que escondia a escalada.
- **CR-02** (a lista fechada contradizendo o loot do mesmo boss): confirmado em `fechar_e_narrar` — a sugestao e **calada** quando `dono_do_loot(loot, alvo)` ja existe.

Suite antes/depois do review: 1003 -> 1051. Reproduzi o 1051.

---

## Human Verification Required

Seis itens, todos colhidos em `10-UAT.md`. Cinco sao julgamento de redacao/legibilidade; um e o **ciclo completo no WhatsApp real** (7 sub-itens), que nenhum teste offline alcanca porque depende do Chatwoot e da ponte Baileys.

Nenhum deles bloqueia o codigo: os comportamentos correspondentes estao provados offline. O que falta e a costura com o mundo real e o julgamento humano sobre a redacao.

---

## Gaps Summary

**Nenhum gap.** Os seis criterios do ROADMAP e os 34 must-haves dos planos estao verdadeiros no codigo, e todos foram demonstrados por execucao — probes proprios com o jogo fechado e sem rede, mais mutacao dos quatro portoes estruturais para provar que eles mordem.

O status e `human_needed` (e nao `passed`) unica e exclusivamente porque a fase carrega itens de verificacao humana que so um humano com um telefone pode fechar. Duas recomendacoes de endurecimento (W-1, W-2) ficam registradas: as duas sao verdadeiras hoje e nao guardadas contra amanha, e as duas cabem num `/gsd-quick` de uma a cinco linhas.

---

*Verified: 2026-08-26*
*Verifier: Claude (gsd-verifier)*
