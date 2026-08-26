---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 03b
subsystem: despacho
tags: [presenca, comandos, despacho, refatoracao, regressao, whatsapp, ast]

# Dependency graph
requires:
  - phase: 10-01
    provides: "`Comando.JOIN`/`LEAVE`, `MensagemDeComando.nick`, `LeitorDeComandos.membros` e `COMANDOS_DE_MEMBRO`"
  - phase: 10-03
    provides: "`RespostaDePresenca(privado, grupo|None)`, `responder_join`, `responder_leave`"
  - phase: 06-agenda-de-eventos
    provides: "`RegistroEmDisco(PASTA_AGENDA)`, que os DOIS lacos ja passam a `atender_comandos`"
provides:
  - "Ramos `Comando.JOIN` e `Comando.LEAVE` em `atender_comandos` — o `.join` deixa de cair no `else: continue`"
  - "Bloco de despacho falando UMA lingua: privado mais grupo-ou-`None`"
  - "`membros=leitor.membros` em `comandos_novos` — o nivel de membro do plano 10-01 deixa de ser codigo inalcancavel"
  - "`tests/test_presenca.py#TestDestinoDosComandosAntigos` — a tabela de destino dos dez ramos antigos, rede permanente contra T-10-21"
  - "`DespachanteQueGrava` / `LeitorDeUmaMensagem` / `despachos_de` — o idioma de testar a costura sem fila, sem thread e sem rede"
affects:
  - 10-04-fechamento-da-lista
  - 10-05-a-lista-sugere-a-vez-do-loot

# Actuals (#2632) — pareia com o `estimate` do plano para calibrar estimativas
# futuras. Base: chars/4 sobre o DIFF realizado (31.965 chars), a MESMA escala
# que o plano usou. O plano estimou raw_tokens 26000 / tokens 52000; o diff
# real deu ~8.0k. Superestimativa de ~3.3x — a QUARTA seguida na mesma direcao
# nesta fase (10-01 ~3x, 10-02 ~4.5x, 10-03 ~4.3x). O numero NAO foi arredondado
# para perto da estimativa: quatro planos errando para o mesmo lado, com a
# razao estavel entre 3x e 4.5x, e um fator de correcao utilizavel, e maquia-lo
# destruiria justamente o dado.
actuals:
  tokens: 7991
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rede de regressao ESCRITA E COMMITADA ANTES da refatoracao, com a invariancia provada por sha256 do bloco da classe entre os dois commits"
    - "Generalizacao por traducao num ponto so (`isinstance` -> tipo comum) em vez de reescrever os N ramos existentes — diff zero nos ramos que nao se quer mexer"
    - "Tabela de casos com guarda derivada do enum: `set(Comando) - COMANDOS_DE_MEMBRO` tem de estar coberta, e o teste diz o NOME do que faltou"
    - "Controle contra prova vazia em teste de autorizacao: o MESMO telefone com e sem `[[membro]]`, para o verde nao vir da falta de trava"
    - "Falso de despachante sincrono gravando `(texto, categoria, conversa)` — mede o DESTINO, nao o transporte"

key-files:
  created: []
  modified:
    - l2scanner/__main__.py
    - tests/test_presenca.py
    - tests/test_comandos.py

key-decisions:
  - "Os oito ramos antigos NAO foram reescritos: a traducao `(str, bool)` -> `RespostaDePresenca` acontece num lugar so, depois da cadeia de `elif`. Diff de zero linha nos ramos que a mitigacao de T-10-21 existe para proteger"
  - "Sem conversa de origem continua saindo UMA mensagem, a do privado. Mandar tambem a redacao de grupo faria o mesmo evento aparecer duas vezes no MESMO destino"
  - "`avisar_o_grupo = True` traduzido como `grupo = privado` — e exatamente o que ele ja significava, e e por isso que a tabela dos tres ramos que ecoam compara os dois textos por IGUALDADE"
  - "Os tres `LeitorFalso` de `test_comandos.py` ganharam `membros` em vez de o codigo de producao usar `getattr(leitor, 'membros', ())`: um falso que nao casa com a interface de producao e o proximo bug de costura esperando"
  - "O helper de teste do party-mate sobrescreve a allowlist de dono para OUTRO numero, e nao para lista vazia — allowlist vazia aceita qualquer um, e o teste ficaria verde medindo a compatibilidade e nao o nivel de membro"
  - "Os telefones de teste tem 8 digitos finais deliberadamente diferentes: o scanner compara por sufixo de 8, e uma colisao entre os numeros de teste faria o party-mate ser aceito como DONO"

patterns-established:
  - "Invariancia de teste provada, nao afirmada: extracao do bloco da classe por AST nas duas revisoes + sha256 (`git diff` do arquivo desde o commit da rede: 279 insercoes, ZERO remocoes)"
  - "Tripwire de arquitetura por AST tambem para COSTURA, e nao so para modulo: `comandos_novos` tem de receber `membros`, e os dois lacos tem de entregar um leitor vindo de `montar_leitor_de_comandos`"

requirements-completed: [PRES-05, PRES-06, PRES-08, PRES-09]

coverage:
  - id: D1
    description: "Os dez ramos de comando ja existentes respondem exatamente onde respondiam antes da refatoracao"
    requirement: "PRES-05"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDestinoDosComandosAntigos::test_destino_de_cada_comando_antigo (10 casos parametrizados)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestDestinoDosComandosAntigos::test_a_tabela_cobre_todo_comando_ANTIGO_do_enum"
        status: pass
      - kind: integration
        ref: "sha256 do bloco da classe identico entre b0f902c (antes) e 9bb45a3 (depois): 1604ec4dae6f922a"
        status: pass
    human_judgment: false
  - id: D2
    description: "Um `.join` de party-mate produz DOIS despachos com textos DIFERENTES: um na origem, um no grupo"
    requirement: "PRES-05"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_join_de_membro_responde_no_privado_E_anuncia_no_grupo"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_leave_de_quem_estava_na_lista_anuncia_no_grupo"
        status: pass
    human_judgment: false
  - id: D3
    description: "Um `.join` repetido produz UM despacho, so na conversa de origem (D-08)"
    requirement: "PRES-06"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_join_repetido_responde_no_privado_e_CALA_no_grupo"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_leave_de_quem_nunca_joinou_responde_so_no_privado"
        status: pass
    human_judgment: false
  - id: D4
    description: "`.join` de um dono fora do `[[membro]]` responde so na origem e nao inventa nick a partir do `sender.name` (D-10)"
    requirement: "PRES-09"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_join_de_dono_fora_do_bloco_membro_NAO_inventa_nick"
        status: pass
    human_judgment: false
  - id: D5
    description: "`comandos_novos` recebe `membros`, e os DOIS lacos entregam um leitor que os carrega"
    requirement: "PRES-08"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestOEloDoNivelDeMembro::test_atender_comandos_passa_membros_para_comandos_novos"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestOEloDoNivelDeMembro::test_os_dois_lacos_entregam_um_leitor_que_carrega_membros (2 casos parametrizados)"
        status: pass
      - kind: integration
        ref: "tests/test_presenca.py#TestDespachoDoJoinEDoLeave::test_sem_o_bloco_membro_o_join_do_party_mate_NAO_atravessa (controle contra prova vazia)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Toda resposta de comando continua saindo com `Categoria.SEMPRE` — nenhuma pode ser cortada pelo silencio de TvT/Prime"
    requirement: "PRES-05"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDestinoDosComandosAntigos::test_todo_destino_antigo_atravessa_o_silencio (10 casos parametrizados)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Um party-mate manda `.join` no privado do bot e ve chegar uma resposta util, enquanto o grupo ve o nick entrar na lista"
    verification: []
    human_judgment: true
    rationale: "Se a linha curta que chega no privado tranquiliza quem digitou, e se o anuncio do grupo diz o suficiente sem virar ruido nas doze ocorrencias por dia, nao e verificavel por teste. Os testes garantem a ESTRUTURA (dois despachos, destinos certos, textos diferentes, nick e horario presentes no do grupo); a qualidade da leitura no WhatsApp so sai olhando."

# Metrics
duration: 35min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 03b: O despacho dos ramos `.join` e `.leave` Summary

**O `.join` deixou de cair no `else: continue` e passou a produzir DUAS redacoes — uma para quem digitou, outra para o grupo — sem que nenhum dos dez ramos de comando ja existentes mudasse de destino, provado por uma tabela escrita, commitada e verde ANTES de o bloco de despacho ser tocado.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 de 2
- **Files modified:** 3 | **created:** 0
- **Suite:** 909 -> **942 passed, 2 skipped** (33 testes novos, nenhum afrouxado)
- **Commits:** 3 (`b0f902c` rede, `60b771d` RED, `9bb45a3` GREEN)

## Accomplishments

- **A ordem invertida do plano funcionou, e a prova esta no git.** A tabela dos dez destinos foi escrita contra o `__main__.py` INTOCADO (`git status --short` no momento do commit `b0f902c` mostrava exatamente um arquivo modificado: `tests/test_presenca.py`) e passou 23/23. Depois da generalizacao ela continua verde **byte a byte identica**: o sha256 do bloco da classe e `1604ec4dae6f922a` nas duas revisoes, e `git diff b0f902c -- tests/test_presenca.py` e **279 insercoes e ZERO remocoes** — nenhuma linha do arquivo inteiro foi alterada, nem os helpers compartilhados.
- **Os oito ramos antigos nao foram tocados.** A generalizacao e uma traducao num lugar so, depois da cadeia de `elif`: o que nao e `RespostaDePresenca` vira `RespostaDePresenca(privado=resposta, grupo=resposta if avisar_o_grupo else None)`. O diff em `l2scanner/__main__.py` nao encosta em nenhum `elif` antigo — o que e a mitigacao mais forte possivel para `T-10-21`, porque o codigo que nao muda nao regride.
- **O nivel de membro deixou de ser codigo inalcancavel.** `comandos_novos` passou a receber `membros=leitor.membros`. Sem essa linha, `Membro`, `nick_do_membro`, `COMANDOS_DE_MEMBRO` e os blocos `[[membro]]` do `config.toml` — tudo entregue verde pelo plano 10-01 — nunca eram consultados, porque `autorizado_para` recebia a tupla vazia por default. O elo esta afirmado por AST **e** por comportamento, com controle: o mesmo telefone SEM `[[membro]]` morre na quinta trava.
- **As duas redacoes chegam ao WhatsApp pela primeira vez no projeto.** Ate aqui `avisar_o_grupo = True` significava "mande o mesmo texto duas vezes". Agora o privado recebe "Anotado. Voce esta na lista..." e o grupo recebe "J4guar vai no Solo Boss das 20:00." — afirmado por desigualdade dos textos, e nao pela frase inteira, para a rede nao gritar em toda melhoria de redacao.
- **`.so-agenda` foi conferido, e nao presumido.** Os dois lacos (`laco_principal` e `laco_da_agenda`) entregam um leitor vindo de `montar_leitor_de_comandos`, e os dois passam um `RegistroEmDisco(PASTA_AGENDA)` — o mesmo objeto que `responder_join` precisa. Ligar o elo so no laco principal deixaria o `.join` funcionando na maquina de quem esta jogando e mudo justamente em quem so quer entrar na lista pelo celular.
- **Zero dependencia nova.** `git diff --stat` contra a base cobre exatamente tres arquivos, nenhum de dependencia.

## Task Commits

1. **Tarefa 1: a rede dos comandos antigos, verde ANTES da refatoracao** — `b0f902c` (test)
2. **Tarefa 2 RED: as duas redacoes no despacho e o elo do nivel de membro** — `60b771d` (test)
3. **Tarefa 2 GREEN: os ramos `.join`/`.leave` e o par de destinos** — `9bb45a3` (feat)

## Files Created/Modified

- **`l2scanner/__main__.py`** (+73 / -5) — import de `presenca`; `membros=leitor.membros` em `comandos_novos`; ramos `Comando.JOIN` e `Comando.LEAVE`; traducao para `RespostaDePresenca` num ponto so; log das duas redacoes, cada uma na sua linha; bloco de despacho falando privado-mais-grupo-ou-`None`.
- **`tests/test_presenca.py`** (+602 no total desta fase) — `DespachanteQueGrava`, `LeitorDeUmaMensagem`, `eventos_classicos`, `despachos_de`, `despachos_do_membro`, `TestDestinoDosComandosAntigos` (24 testes) e `TestDespachoDoJoinEDoLeave` + `TestOEloDoNivelDeMembro` (10 testes).
- **`tests/test_comandos.py`** (+12) — os tres `LeitorFalso` ganharam `membros`, com o comentario dizendo de onde a exigencia veio.

## Decisions Made

- **A generalizacao e uma traducao, e nao uma reescrita.** A alternativa obvia era fazer cada ramo antigo devolver `RespostaDePresenca` — dez edicoes num arquivo com ~19% de cobertura, cada uma uma chance de trocar um destino em silencio. A traducao por `isinstance` num ponto so custa uma linha de codigo e tem a propriedade que interessa: **o diff nao encosta nos ramos que se quer proteger.**
- **Sem conversa de origem continua saindo UMA mensagem.** Hoje, uma mensagem sem `conversation_id` cai no grupo com o texto unico. Com o par, a tentacao era mandar os dois — e isso faria o mesmo evento aparecer duas vezes no MESMO destino. A regra ficou escrita em comentario ao lado do `else`.
- **`getattr(leitor, "membros", ())` foi rejeitado.** Ele teria feito o codigo de producao passar sem tocar em nenhum falso de teste — e teria deixado tres falsos permanentemente divergentes da interface real. Neste projeto os erros moram na COSTURA, e um falso que nao casa com producao e o proximo bug de costura esperando. Os tres ganharam `membros`.
- **O helper de party-mate sobrescreve a allowlist de dono para OUTRO numero.** Lista vazia aceita qualquer um (compatibilidade documentada em `autor_autorizado`), entao um teste com allowlist vazia ficaria verde sem provar nada sobre o `[[membro]]`. Os 8 digitos finais dos dois telefones de teste sao deliberadamente diferentes, porque o scanner compara por sufixo de 8 e uma colisao ali faria o party-mate entrar como dono.
- **`Categoria.SEMPRE` virou afirmacao explicita da tabela.** Ela ja era verdade, mas nao estava escrita em teste nenhum. Uma resposta de comando cortada pelo silencio de TvT/Prime seria a mesma falha silenciosa do destino errado vestida de outra roupa: quem digitou nao recebe nada e conclui que o bot morreu, justo quando ele esta calado de proposito.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tres `LeitorFalso` de `test_comandos.py` nao tinham `membros`**

- **Found during:** Tarefa 2, GREEN
- **Issue:** `atender_comandos` passou a ler `leitor.membros`. Os tres leitores falsos de `tests/test_comandos.py` (linhas ~932, ~1004, ~1188) declaravam so `ativo` e `telefones`, e quebrariam com `AttributeError` — e `atender_comandos` nao captura excecao no corpo do laco, entao seria crash e nao silencio.
- **Fix:** Cada um ganhou `membros: list = []`, com o comentario dizendo por que o campo existe e por que esta vazio ali (aqueles testes sao sobre o nivel de DONO). Nenhuma asserção foi tocada; nenhum teste foi afrouxado.
- **Files modified:** `tests/test_comandos.py`
- **Verification:** `python -m pytest tests/test_comandos.py -q` -> 131 passed.
- **Committed in:** `9bb45a3`

---

**Total deviations:** 1 auto-fixada (blocking). Nenhuma mudanca de escopo, nenhuma assinatura publica alterada, nenhum simbolo novo em modulo de biblioteca — como o `<artifacts_produced>` do plano determinou.

## Issues Encountered

- **O caso do plano listava dez sintaxes sob o rotulo "nove comandos".** A tabela do `<interface_context>` tem dez linhas (`.solo` e `.party` sao duas), e o enum tem dez ramos antigos. A tabela do teste cobre as **dez**, e a guarda derivada (`set(Comando) - COMANDOS_DE_MEMBRO`) confirma que nenhuma ficou de fora — foi ela que resolveu a ambiguidade em vez de uma contagem digitada a mao.
- **Um dos testes da Tarefa 2 passa hoje pelo motivo certo e passava ontem pelo motivo errado.** `test_sem_o_bloco_membro_o_join_do_party_mate_NAO_atravessa` era verde no commit RED porque NADA era despachado. Ele so vira prova de verdade ao lado do teste que ele controla — os dois foram commitados juntos e sao lidos juntos. Registrado para o proximo leitor nao tomar aquele verde do RED como evidencia isolada.
- **Ruff continua acusando erros pre-existentes em outros arquivos de teste**, como os planos 10-01 e 10-03 ja registraram. `ruff check` sobre os tres arquivos desta fase passa limpo. Fora do escopo por regra (SCOPE BOUNDARY); nao foram tocados.

## Known Stubs

Nenhum stub. Uma ausencia INTENCIONAL, escrita no plano 10-03 e ainda valendo:

1. `RegistroEmDisco.fechar` existe, esta testado e continua sem chamador — quem dispara o fechamento no horario do boss e o plano **10-04**. `PREFIXO_FECHADO` ja e conhecido pela poda, entao nenhum marcador nasce imortal enquanto isso.

O efeito colateral herdado dos planos 10-01 e 10-03 — um `.join` marcado como obedecido em `.agenda/` e sem resposta nenhuma — **acabou aqui**. Um `.join` de party-mate agora atravessa e responde nos dois destinos.

## Threat Flags

Nenhuma superficie de seguranca nova fora do `<threat_model>` do plano. As mitigacoes previstas foram aplicadas:

| Threat ID | Disposition | Onde ficou |
|---|---|---|
| T-10-21 (destino de um ramo antigo trocado em silencio) | mitigado | `TestDestinoDosComandosAntigos`, escrita e commitada ANTES da refatoracao (`b0f902c`), verde depois **sem uma linha alterada** (sha256 `1604ec4dae6f922a` nas duas revisoes). Reforcado pelo fato de o diff de producao nao encostar em nenhum `elif` antigo |
| T-10-11 (`.join` repetido enchendo o grupo) | mitigado | O tri-estado do plano 10-03 devolve `grupo is None`; `test_join_repetido_responde_no_privado_e_CALA_no_grupo` **conta** os despachos |
| T-10-22 (nick inventado quando `pedido.nick` e `None`) | mitigado | O ramo repassa `None` inteiro; `test_join_de_dono_fora_do_bloco_membro_NAO_inventa_nick` afirma que `"Yazalaque"` (o `sender.name`) nao aparece na resposta |
| T-10-SC (instalacao de pacote) | mitigado | Zero dependencia nova; `git diff --stat` cobre tres arquivos, nenhum de dependencia |

Uma superficie que MUDOU e merece registro sem ser flag nova: `comandos_novos` passou a receber `membros`, o que significa que os telefones do `config.toml` viraram, de fato, autorizacao ativa. Isso e o objetivo declarado de `PRES-08`, e a fronteira que o limita (`COMANDOS_DE_MEMBRO`, lista de INCLUSAO) e a prova de recusa derivada do enum ja estavam verdes desde o plano 10-01.

## User Setup Required

Nenhuma configuracao de servico externo. Para os party-mates darem `.join`, o usuario descomenta os blocos `[[membro]]` no `config.toml` e poe nick + telefone de cada um — a partir deste plano, esses blocos passam a ter efeito. O `chamar_minutos_antes = 110` do Solo Boss ja entrou no `config.toml` no plano 10-02.

## Next Phase Readiness

Pronto para 10-04 e 10-05. O que eles herdam:

- **10-04** recebe uma lista que agora tem CONTEUDO em producao: `registro.presentes(chave)` passa a devolver gente de verdade, porque o `.join` finalmente grava. `fechar`, `presentes` e `nomes_dos_membros` continuam prontos e sem chamador.
- **10-05** recebe o mesmo, mais o idioma de teste da costura (`DespachanteQueGrava`, `LeitorDeUmaMensagem`, `despachos_de`) para exercitar `atender_comandos` sem fila, sem thread e sem rede — e a tabela de destino ja instalada como rede para qualquer ramo novo que precise ecoar no grupo.

Sem blockers.

## Self-Check: PASSED

- Arquivos afirmados existem: `l2scanner/__main__.py`, `tests/test_presenca.py`, `tests/test_comandos.py`, `10-03b-SUMMARY.md`.
- Commits afirmados existem: `b0f902c`, `60b771d`, `9bb45a3`.
- `python -m pytest tests/ -q` -> **942 passed, 2 skipped** (linha de base 909; os 2 skips sao pre-existentes).
- `python -m pytest tests/test_presenca.py -q -k "destino"` -> 23 passed.
- Invariancia da Tarefa 1: bloco da classe extraido por AST em `b0f902c` e no worktree, 6987 chars e sha256 `1604ec4dae6f922a` nos dois. `git diff b0f902c -- tests/test_presenca.py` -> 279 insercoes, 0 remocoes.
- `python -c "import l2scanner.__main__, l2scanner.presenca, l2scanner.loot, l2scanner.comandos"` -> ok, sem ciclo.
- `python -m ruff check` sobre os tres arquivos desta fase -> limpo.
- `git diff --stat` contra a base cobre 3 arquivos; nenhum de dependencia.
- `git diff --diff-filter=D` no commit GREEN -> nenhuma delecao.
- `STATE.md` e `ROADMAP.md` NAO foram modificados — o orquestrador e o dono dessas escritas.

---
*Phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp*
*Completed: 2026-08-26*
