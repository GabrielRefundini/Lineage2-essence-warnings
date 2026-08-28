---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Ponte Discord
current_phase: 1
current_phase_name: Ponte viva — conexao provada e texto real
current_plan: 2
status: executing
stopped_at: "Completado 01-01-PLAN.md (onda 1). Ondas 2 e 3 (01-02, 01-03) nao comecaram."
last_updated: "2026-08-28T17:30:00.000Z"
last_activity: 2026-08-28
last_activity_desc: "01-01 executado: discord.py auditado e instalado, tres modulos, .bat e roteiro do portao humano"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 11
---

# Project State

## Project Reference

**Core value:** Quem nao abre o Discord fica sabendo do anuncio no WhatsApp, em segundos.
**Current focus:** Phase 1 — Ponte viva: conexao provada e texto real
**Workstream:** discord (paralelo a `mercado` e `default` no mesmo branch)

## Current Position

Phase: 1 (Ponte viva — conexao provada e texto real) — EXECUTING
Plan: 01-01 COMPLETO. Proximo: 01-02 (onda 2), depois 01-03 (onda 3)
Status: A fatia ponta a ponta existe e esta verde. O criterio 2 da fase segue PENDENTE no portao humano.
Last activity: 2026-08-28 — 01-01 executado (4 commits, 1708 insercoes, zero delecoes)

Progress: [█░░░░░░░░░] 11% (1 de 3 planos da Fase 1)

## Accumulated Context

### Decisions

- 3 fases (granularity: coarse). A divisao e vertical por etapa do caminho da mensagem: receber → formatar → entregar. Nada de camada horizontal.
- Fase 1 nao formata e nao entrega. Ela existe para provar o portao humano (intent MESSAGE CONTENT) com texto real no console antes que qualquer coisa seja construida em cima.
- ENTR-04 (nunca entregar duas vezes) vive na Fase 1, nao na Fase 3: o livro de ja-vistos decide como a mensagem recebida e identificada logo na PRIMEIRA linha do caminho de recebimento. Adiar custaria reescrever esse caminho no primeiro restart.
- CONF-04 (modo simulacao) vive na Fase 1: e o que torna o criterio do portao humano conferivel sem incomodar o grupo do WhatsApp. Na Fase 1 a ponte SO simula.
- A dependencia nova do Discord entra na Fase 1, com `tests/test_firewall_escopo.py` rodando verde na mesma fase — a banlist passa, mas isso e para se ver passando.
- Modulo, entrypoint e `.bat` proprios. `l2scanner/__main__.py` (editado pelo workstream `mercado`) e `l2scanner/notificador.py` nao sao tocados. Alem do merge, e a arquitetura certa: ponte async orientada a evento vs scanner sincrono de 1 Hz.
- Idioma: portugues sem acento em codigo, teste, commit e prosa de planejamento. Modulo no idioma do repo (`ponte_discord`, ao lado de `notificador`, `presenca`, `rastreador`).
- Slugs de fase levam prefixo `discord-` para nao colidir com escopos de commit dos workstreams `mercado` e `default`.
- Pesquisa de dominio pulada de proposito: `.planning/research/` e compartilhado e sobrescreveria os 220 KB da pesquisa do workstream `mercado`.
- **(01-01)** A biblioteca cliente e `discord.py` 2.7.1 de Rapptz, MIT — portao de legitimidade aprovado pelo usuario ("Autorizo, e o pacote certo") depois de os vizinhos `discord`/`discordpy`/`discord-py` terem sido nomeados. Declarada DIRETO no `requirements.txt`; um `-r` faria o firewall de escopo levantar `AssertionError` por construcao.
- **(01-01)** Instalacao no `.venv` sempre pelo NOME e pela faixa, nunca `-r requirements.txt`: os pinos do scanner sao abertos, e um `-r` durante o farm reescreveria `cv2.pyd` e as DLLs do `numpy` com elas carregadas. Medido: `pip list` antes/depois teve 10 adicoes e ZERO alteracoes.
- **(01-01)** A divisao em tres modulos e por AMBIENTE, nao por camada: `ponte_config.py` e `ponte_nucleo.py` sao stdlib pura porque o pytest roda no Python GLOBAL (sem `discord`), e so `ponte_discord.py` escreve `import discord`. Ha teste de subprocesso guardando isso.
- **(01-01)** O `on_ready` chama `definir_id_da_ponte(self.user.id)` ANTES de logar. Sem isso o filtro da PONTE-04 fica verde no teste e morto em producao, e o sintoma so apareceria na Fase 3 como laco de entrega.
- **(01-01)** O `ponte-discord.bat` CONFERE e RECUSA; quem monta o ambiente e so o `vigiar-party.bat`. Ha teste varrendo as linhas executaveis do `.bat` (descartando `REM`) para que a promessa nao dependa de comentario.
- **(01-01)** O `.bat` novo e ASCII PURO: medido, a raiz mistura cp1252 (`calibrar-mercado.bat`) e utf-8 (`avisos-tvt.bat`, `vigiar-party.bat`), entao qualquer byte fora do ASCII apareceria quebrado para metade dos leitores.
- **(01-01)** `conversa_de_destino` vazia continua sendo config VALIDA na Fase 1: exigir o id agora impediria o proprio criterio 2 de ser conferido, ja que a fase so simula.

### Blockers

- **Fase 1 bloqueia no portao humano.** Os 4 passos so o USUARIO pode fazer: criar a aplicacao no Discord, ligar a intent **MESSAGE CONTENT**, convidar o bot para XM Games com `View Channel` + `Read Message History`, e informar o `conversation_id` do Chatwoot de destino. Sem a intent, a ponte conecta, parece saudavel e replica mensagem em branco para sempre — o modo de falha mais caro do milestone. O criterio 2 da Fase 1 fica pendente ate isso acontecer, e a Fase 2 nao deve ser planejada em detalhe antes dele estar conferido.

### Todos

- [ ] Aprovacao do roadmap pelo usuario (orquestrador commita depois)
- [x] Decidir na Fase 1 o nome do `.bat` da raiz — ficou `ponte-discord.bat` (01-01)
- [x] Escolher e travar a biblioteca cliente do Discord — `discord.py>=2.7.1,<3` (01-01)
- [ ] **O USUARIO precisa dar os 4 passos do `PORTAO-DISCORD.txt`.** Ate la o criterio 2 da Fase 1 fica PENDENTE e PONTE-01/PONTE-05 nao podem ser marcadas.

## Session Continuity

**Stopped At:** Completado 01-01-PLAN.md (onda 1). As ondas 2 e 3 nao comecaram.
**Resume File:** .planning/workstreams/discord/phases/01-ponte-viva-conexao-provada-e-texto-real/01-02-PLAN.md
**Next:** executar `01-02-PLAN.md` (onda 2) e depois `01-03-PLAN.md` (onda 3) — os tres escrevem em `ponte_nucleo.py`/`ponte_discord.py`, entao rodam em serie.

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| 01-01 | ~28 min | 4 | 11 |
