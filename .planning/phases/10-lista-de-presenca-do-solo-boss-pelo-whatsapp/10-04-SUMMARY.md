---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 04
subsystem: presenca
tags: [presenca, agenda, fechamento, whatsapp, duas-instancias, ast, tdd]

# Dependency graph
requires:
  - phase: 10-03
    provides: "`presenca.py`, `ocorrencia_recem_fechada`, `nomes_dos_membros`, e o gate de AST parametrizado sobre os tres modulos"
  - phase: 10-03b
    provides: "`RespostaDePresenca` e o despacho generalizado — o `.join` que ENCHE a lista que este plano fecha"
  - phase: 10-02
    provides: "`TipoDeAviso.CHAMADA` — a pergunta feita 1h50 antes, que agora tem desfecho"
  - phase: 06-agenda-de-eventos
    provides: "`RegistroEmDisco.fechar`/`marcar` (`O_CREAT|O_EXCL`), `TOLERANCIA_MINUTOS`, `chave_da_ocorrencia`"
  - phase: 08-loot-do-solo-boss
    provides: "`RegistroDeLoot.consumir` — o analogo de 'o horario passou, esta instancia venceu a corrida'"
provides:
  - "`presenca.Fechamento(evento, alvo, nicks)` — a lista de uma ocorrencia, estruturada e congelada"
  - "`presenca.fechar_ocorrencias(registro, eventos, agora)` — le os presentes ANTES de marcar, e cala com lista vazia"
  - "`presenca.texto_de_fechamento(fechamento, nomes, sugestao)` — o `sugestao` nasce declarado e ignorado, para o plano 10-05"
  - "`presenca.ocorrencias_na_janela` — a varredura de janela extraida de `ocorrencia_recem_fechada`, agora devolvendo TODAS"
  - "`sessao.ResultadoDoTick.presencas_fechadas` — estruturado, nunca o texto"
  - "`sessao.Sessao(..., membros=())` — os `[[membro]]` chegando a lista fechada (D-10)"
  - "`__main__._fechar_listas_de_presenca` — o mesmo fechamento no laco `--so-agenda`, com o jogo fechado"
affects:
  - 10-05-a-lista-sugere-a-vez-do-loot

# Actuals (#2632) — pareia com o `estimate` do plano para calibrar estimativas
# futuras. Base: chars/4 sobre o DIFF realizado em `l2scanner/` + `tests/`
# (42.330 chars), a MESMA escala que o plano usou. O plano estimou
# raw_tokens 35000 / tokens 70000; o diff real deu ~10.6k. Superestimativa de
# ~3.3x sobre o raw — a QUINTA seguida na mesma direcao nesta fase
# (10-01 ~3x, 10-02 ~4.5x, 10-03 ~4.3x, 10-03b ~3.3x). Cinco planos errando
# para o mesmo lado, com a razao estavel entre 3x e 4.5x, e um fator de
# correcao utilizavel; o numero NAO foi arredondado para perto da estimativa,
# porque maquia-lo destruiria justamente o dado.
actuals:
  tokens: 10583
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ordem entre ler e marcar como DECISAO nomeada, com teste que falha na ordem errada e diz por que (troca da ordem no fonte quebra exatamente 2 testes, com a mensagem 'o marcador foi queimado cedo demais')"
    - "Extrair a varredura de janela e alargar o retorno (um -> todos) em vez de duplicar o laco: `ocorrencia_recem_fechada` vira `achados[-1]`"
    - "Parametro que nasce declarado e ignorado, com o precedente citado no codigo (`EventoAgendado.silenciar_minutos`, Fase 6) para ninguem apagar achando que e codigo morto"
    - "Guarda contra prova vazia sobre o FIXTURE: `test_o_evento_de_teste_tem_o_aviso_de_agora_DESLIGADO` impede que alguem ligue `avisar_no_horario` e faca o fechamento sair de carona sem ninguem notar"
    - "Funcao extraida do corpo do laco `--so-agenda` (19-20% de cobertura) + tripwire de AST afirmando que o laco a CHAMA — funcao testada e nunca chamada e o modo de falha caro desta fase"

key-files:
  created: []
  modified:
    - l2scanner/presenca.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_presenca.py
    - tests/test_sessao.py

key-decisions:
  - "Ler `presentes` ANTES do `fechar`. Marcar primeiro queimaria o marcador num tick de lista vazia, e um `.join` entregue tres segundos depois do alvo — ainda dentro da tolerancia de 5 min — nunca viraria mensagem. A garantia contra duplicata nao se perde: o `fechar` continua sendo a linha que decide quem fala"
  - "O fechamento NAO passa por `avisos_devidos`. O criterio e `chamar_minutos_antes > 0`, o mesmo que criou a lista — o Solo Boss do usuario segue com `avisar_no_horario = false` e fecha do mesmo jeito (D-12)"
  - "`Categoria.SEMPRE` e nao `NORMAL`: a lista fechada e organizacao de party, e nao alerta de morte. Silencia-la dentro de uma janela de Prime esconderia justamente a mensagem que diz quem esta indo"
  - "O fechamento vem por ULTIMO em `_processar_agenda`, depois do consumo de loot, porque no plano 10-05 ele passa a depender do que o consumo acabou de registrar"
  - "Diferente do consumo de loot no mesmo laco `--so-agenda` (que e 'SO LOG, sem WhatsApp'), a lista fechada VAI para o grupo: ela e o desfecho da pergunta feita 1h50 antes, e o volume nao e o mesmo problema porque o piso e silencio"
  - "`ocorrencias_na_janela` devolve LISTA e nao um so, e `ocorrencia_recem_fechada` virou `achados[-1]`: o `.leave` quer a mais recente (uma recusa), o fechamento quer todas"
  - "Um slug fora do mapa `[[membro]]` cai em `exibir(slug)` e nunca e filtrado — um party-mate sem bloco no config nao pode SUMIR da lista"
  - "Extrair `_fechar_listas_de_presenca` do corpo do laco em vez de escreve-la inline: o `--so-agenda` esta em 19-20% de cobertura, e um fechamento escrito la dentro nasceria sem teste justamente no modo que faz o recurso valer"

patterns-established:
  - "Teste de ordem provado por inversao: a troca de `presentes`/`fechar` no fonte foi executada e derrubou exatamente os dois testes previstos, com a mensagem de falha nomeando a causa"
  - "Tripwire de AST para ALCANCE, e nao so para direcao de import: `laco_da_agenda` tem de chamar `_fechar_listas_de_presenca`, e TODA construcao de `Sessao` tem de passar `membros`"

requirements-completed: [PRES-12]

coverage:
  - id: D1
    description: "No horario do boss a lista fecha e o grupo recebe quem confirmou"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoDaLista::test_fecha_com_a_lista_cheia_e_devolve_todo_mundo"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_o_tick_do_horario_fecha_a_lista"
        status: pass
      - kind: integration
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_lista_cheia_produz_exatamente_um_despacho_no_grupo"
        status: pass
    human_judgment: false
  - id: D2
    description: "Zero confirmacoes produz ZERO mensagem — nenhum despacho, nenhum aviso, e nenhum arquivo novo em disco (D-12)"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoDaLista::test_lista_vazia_nao_fecha_nem_escreve_nada_em_disco (compara o conteudo da pasta antes e depois)"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_zero_confirmacoes_produz_ZERO_de_tudo"
        status: pass
      - kind: integration
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_lista_vazia_produz_zero_despacho_e_zero_log"
        status: pass
    human_judgment: false
  - id: D3
    description: "O fechamento NAO depende de `avisar_no_horario`: o Solo Boss do usuario segue com o campo em false e a lista fecha do mesmo jeito (D-12)"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoDaLista::test_avisar_no_horario_desligado_fecha_do_mesmo_jeito"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick (o `SOLO` da classe tem `avisar_no_horario=False`; todos os 9 casos correm sobre ele)"
        status: pass
      - kind: unit
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_o_evento_de_teste_tem_o_aviso_de_agora_DESLIGADO (guarda contra prova vazia sobre o fixture)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Com as duas instancias do usuario rodando, o grupo recebe a lista fechada UMA vez"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoDaLista::test_a_segunda_instancia_do_usuario_nao_fecha_de_novo (dois `RegistroEmDisco` sobre a MESMA pasta)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoDaLista::test_dois_ticks_seguidos_fecham_uma_vez_so"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_dois_ticks_dentro_da_janela_fecham_uma_vez_so (T-10-16)"
        status: pass
      - kind: integration
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_duas_voltas_do_laco_fecham_uma_vez_so"
        status: pass
    human_judgment: false
  - id: D5
    description: "A lista fechada sai com a grafia do nick que esta no `config.toml`, nao com a caixa do slug (D-10)"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestTextoDeFechamento::test_com_o_mapa_sai_a_grafia_do_config"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_com_membros_a_lista_sai_com_a_grafia_do_config"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_a_sessao_do_laco_principal_recebe_membros (AST: toda construcao de `Sessao` passa `membros`)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestTextoDeFechamento::test_slug_fora_do_mapa_ainda_aparece (controle: sem bloco `[[membro]]` a pessoa nao some)"
        status: pass
    human_judgment: false
  - id: D6
    description: "O fechamento acontece tambem em `--so-agenda`, com o jogo fechado"
    requirement: "PRES-12"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_o_laco_da_agenda_chama_o_fechamento (AST: a funcao existir nao basta, o laco tem de chama-la)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_sem_despachante_o_fechamento_ainda_aparece_no_log"
        status: pass
    human_judgment: false
  - id: D7
    description: "A lista sai nas conversas de AVISO e nunca numa conversa de comando (T-10-17)"
    verification:
      - kind: unit
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_o_console_recebe_o_texto_CRU_e_o_whatsapp_a_moldura (afirma `conversa is None` e `Categoria.SEMPRE`)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestFechamentoComOJogoFechado::test_lista_cheia_produz_exatamente_um_despacho_no_grupo"
        status: pass
    human_judgment: false
  - id: D8
    description: "A redacao da lista fechada le bem no WhatsApp do grupo, sem virar ruido nas doze ocorrencias por dia"
    verification: []
    human_judgment: true
    rationale: "Os testes garantem a ESTRUTURA (evento, horario e todos os nicks presentes; grafia do config; sem acento, sem quebra de linha, dentro da moldura, uma vez so). Se 'Solo Boss das 20:00 comecando. Confirmaram: J4guar, TioMad.' e a frase certa para quem esta no meio do farm olhando o celular, so sai olhando o grupo de verdade."

# Metrics
duration: 20min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 04: O fechamento da lista de presenca Summary

**A pergunta feita 1h50 antes ganhou desfecho: no horario do boss a lista fecha e o grupo recebe quem confirmou — uma vez so entre as duas instancias, sem depender do `avisar_no_horario` que o usuario desligou, e em ABSOLUTO silencio quando ninguem joinou, provado por comparacao do conteudo da pasta `.agenda/` antes e depois.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 de 3
- **Files modified:** 5 | **created:** 0
- **Suite:** 942 -> **976 passed, 2 skipped** (34 testes novos, nenhum afrouxado)
- **Commits:** 5 (`ca684d8` RED, `649e6db` GREEN, `1d067c2` RED, `289dfc1` GREEN, `a1afcb1` feat)

## Accomplishments

- **A decisao de ordem foi tomada, justificada por escrito, e PROVADA por inversao.** `fechar_ocorrencias` le `registro.presentes(chave)` antes de chamar `registro.fechar(chave)`. Para confirmar que o teste nao e decorativo, a ordem foi invertida no fonte e a suite rodada: caem exatamente dois testes — `test_lista_vazia_nao_fecha_nem_escreve_nada_em_disco` e `test_join_entregue_depois_do_alvo_ainda_vira_fechamento` — o segundo com a mensagem `"o marcador foi queimado cedo demais: o tick de lista vazia fechou a ocorrencia, e o .join entregue tres segundos depois nunca virou mensagem nenhuma"`. A ordem foi restaurada e os 19 voltaram ao verde.
- **Zero confirmacoes produz zero de tudo, medido em disco.** `test_lista_vazia_nao_fecha_nem_escreve_nada_em_disco` compara `sorted(tmp_path.iterdir())` antes e depois da chamada. Um `fechar_ocorrencias` que devolvesse lista vazia mas gravasse o marcador passaria numa afirmacao sobre o retorno e quebraria o teste do `.join` atrasado — a comparacao da pasta e o que fecha esse buraco. No tick e no laco `--so-agenda` a mesma propriedade e afirmada sobre `avisos`, `despachos` e `presencas_fechadas`.
- **O fechamento nao encosta em `avisos_devidos`, e ha guarda contra alguem religar o fixture.** O `SOLO` de `TestPresencaNoTick` tem `avisar_no_horario=False`, como o `config.toml` real do usuario, e os nove casos da classe correm sobre ele. Um teste separado — `test_o_evento_de_teste_tem_o_aviso_de_agora_DESLIGADO` — afirma o campo, para que um dia alguem "consertando" o fixture nao faca o fechamento sair de carona no aviso de AGORA sem ninguem notar.
- **A corrida das duas instancias esta afirmada nos tres niveis.** No registro (dois `RegistroEmDisco` sobre a mesma `tmp_path`), no tick (dois ticks dentro da janela de 5 min) e no laco da agenda (duas voltas). A 1 Hz, sem o marcador, cada ocorrencia produziria ~300 mensagens — que e exatamente o `T-10-16` do registro de ameacas.
- **`--so-agenda` ganhou o fechamento com teste, e um tripwire contra a funcao orfa.** `_fechar_listas_de_presenca` foi extraida do corpo do laco (que esta em 19-20% de cobertura) e e exercitavel sem relogio, sem rede e sem jogo. Mas funcao testada e nunca chamada e o modo de falha caro desta fase — o mesmo que deixou o nivel de membro inalcancavel no plano 10-01 — entao um teste de AST afirma que `laco_da_agenda` a CHAMA, e outro afirma que TODA construcao de `Sessao` passa `membros`. Os dois falharam no RED.
- **`ocorrencia_recem_fechada` nao foi duplicada: foi alargada.** A varredura virou `ocorrencias_na_janela`, que devolve todas as ocorrencias da janela ordenadas pelo alvo, e `ocorrencia_recem_fechada` virou `achados[-1] if achados else None`. Os dois leitores querem coisas diferentes — o `.leave` quer a mais recente para recusar, o fechamento quer todas — e um segundo laco copiado teria feito as duas varreduras divergirem na primeira mudanca de tolerancia.
- **A frase nova entrou na rede de forma que ja existia.** `texto_de_fechamento` foi acrescentada a `TestFormaDoTexto.todas_as_frases`, entao ela passa pelos mesmos gates de "sem acento", "sem quebra de linha" e "nao vazia" que as onze frases anteriores. Uma varredura independente sobre TODAS as linhas adicionadas em `l2scanner/` e `tests/` confirmou zero caracteres acentuados.
- **Zero dependencia nova.** `git diff --stat` contra a base cobre exatamente cinco arquivos, nenhum de dependencia.

## Task Commits

1. **Tarefa 1 RED: a lista vazia que nao gasta o marcador** — `ca684d8` (test)
2. **Tarefa 1 GREEN: `Fechamento`, `fechar_ocorrencias`, `texto_de_fechamento`** — `649e6db` (feat)
3. **Tarefa 2 RED: o tick que fecha e o tick que cala** — `1d067c2` (test)
4. **Tarefa 2 GREEN: `presencas_fechadas`, `Sessao(membros=)`, o fechamento em `_processar_agenda`** — `289dfc1` (feat)
5. **Tarefa 3: `_fechar_listas_de_presenca` no `--so-agenda` e `membros` na `Sessao`** — `a1afcb1` (feat)

## Files Created/Modified

- **`l2scanner/presenca.py`** (+150 / -17) — `ocorrencias_na_janela` extraida e alargada; `ocorrencia_recem_fechada` reduzida a `achados[-1]`; `Fechamento` (frozen, `nicks` em slug ordenado); `fechar_ocorrencias` com a decisao de ordem na docstring, com o caso concreto e com a nota de que a garantia contra duplicata nao se perde; `texto_de_fechamento(fechamento, nomes, sugestao)` com o precedente do `silenciar_minutos` citado no codigo.
- **`l2scanner/sessao.py`** (+45) — import de `presenca`; `ResultadoDoTick.presencas_fechadas`; `Sessao(..., membros=())`; o fechamento em `_processar_agenda` depois do consumo de loot, CRU em `avisos` e MOLDURADO no despacho, `Categoria.SEMPRE`, sem conversa alvo.
- **`l2scanner/__main__.py`** (+59) — import de `fechar_ocorrencias`/`nomes_dos_membros`/`texto_de_fechamento`; `_fechar_listas_de_presenca` extraida; chamada no laco `--so-agenda` logo depois do consumo de loot; `membros=leitor_de_comandos.membros if leitor_de_comandos else ()` na construcao da `Sessao`.
- **`tests/test_presenca.py`** (+382) — `TestFechamentoDaLista` (12), `TestTextoDeFechamento` (6), `TestFechamentoComOJogoFechado` (7); `texto_de_fechamento` acrescentada a `TestFormaDoTexto.todas_as_frases`; `import logging` para os dois casos de `caplog`.
- **`tests/test_sessao.py`** (+180) — `TestPresencaNoTick` (9), `membros` no helper `nova_sessao`, `chave_da_ocorrencia` no import da agenda.

## Decisions Made

- **Ler antes de marcar, e a razao esta no codigo.** O `marcar` do `RegistroEmDisco` diz na propria docstring que a decisao de despachar tem que ser ELE, nunca uma checagem anterior — e isso continua verdade. Mas D-12 acrescenta uma segunda regra que a primeira sozinha nao satisfaz: zero confirmacoes produz zero mensagem. Marcar primeiro atenderia a primeira e quebraria a segunda no caso concreto do `.join` entregue as 20:00:03 pela ponte do Chatwoot. Lendo antes, um tick de lista vazia nao toca em disco e o proximo tick que enxergar alguem fecha e anuncia; a exclusividade entre as instancias fica intacta porque o `fechar` continua sendo a linha que decide quem fala.
- **`Categoria.SEMPRE`, e nao `NORMAL`.** A lista fechada e organizacao de party, e nao alerta de morte. Marca-la como `NORMAL` a faria ser cortada no transporte dentro de uma janela de silencio de Prime — e o Prime de segunda a quinta vai das 20:00 as 22:00, que e onde metade das ocorrencias do Solo Boss caem. O silencio esconderia justamente a mensagem que diz quem esta indo.
- **O fechamento por ULTIMO em `_processar_agenda`.** A ordem e indiferente no relogio hoje, mas fixa-la torna o tick deterministico para o teste — o mesmo argumento que o consumo de loot ja carrega tres linhas acima. A posicao especifica (depois do loot) nao e arbitraria: no plano 10-05 o fechamento passa a depender do que o consumo acabou de registrar, entao ele precisa enxergar o disco ja atualizado.
- **No `--so-agenda`, a lista VAI para o WhatsApp — ao contrario do consumo de loot logo acima.** Aquele e "SO LOG, sem WhatsApp" por disciplina de volume. Aqui a regra se inverte porque o fato e outro: a lista fechada e o desfecho da pergunta que a chamada fez no grupo 1h50 antes, e deixa-la so no console deixaria a party sem a resposta. O volume nao e o mesmo problema, porque o piso e silencio (D-12) e nao doze mensagens por dia.
- **Extrair a funcao do laco, e nao escreve-la inline.** O `--so-agenda` esta na faixa de 19-20% de cobertura — foi onde os tres warnings do code review moravam. Um fechamento escrito la dentro nasceria sem teste nenhum, justamente no modo que faz o recurso valer para quem nao esta com o jogo aberto. Fora do laco ele custa cinco testes e nenhum relogio.
- **`sugestao` nasce declarada e ignorada, com o precedente citado no codigo.** Nao e codigo morto: e o mesmo movimento literal de `EventoAgendado.silenciar_minutos`, que nasceu na Fase 6 lido e ignorado para a Fase 7 usar sem o usuario ter que reeditar nada. A docstring escreve o precedente para ninguem apagar o parametro numa limpeza.
- **Slug fora do mapa `[[membro]]` cai em `exibir(slug)` e nao e filtrado.** Um party-mate sem bloco no `config.toml` sairia da lista se o mapa fosse tratado como filtro — a party leria "Confirmaram: J4guar." e nao saberia que o outro tambem vai. Cosmetico e visivel e melhor do que correto e mudo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O teste de virada de meia-noite usava um horario cuja janela nao atravessa o dia**

- **Found during:** Tarefa 1, GREEN
- **Issue:** O caso escrito no RED usava um boss as 23:50 fechando as 00:02 do dia seguinte. Com `TOLERANCIA_MINUTOS = 5`, a janela de um boss as 23:50 termina as 23:55 — antes da meia-noite. O teste falhava, mas por um defeito NO TESTE: ele nao exercitava o ramo `deslocamento = -1` que pretendia cobrir, porque nenhuma janela chegava la.
- **Fix:** O horario passou para 23:58, cuja janela termina as 00:03 e portanto atravessa a meia-noite de verdade. A docstring do teste passou a dizer por que os dois minutos nao sao folga arbitraria: 23:58 e o ultimo horario cheio cuja janela cruza o dia com a tolerancia de 5 minutos.
- **Files modified:** `tests/test_presenca.py`
- **Verification:** `python -m pytest tests/test_presenca.py -q` -> 103 passed.
- **Committed in:** `649e6db`

Nenhuma outra deviacao: o codigo de producao dos tres arquivos saiu como o plano descreveu.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. As tres mitigacoes com disposicao `mitigate` estao afirmadas por teste:

| Threat | Disposicao | Onde esta afirmada |
|---|---|---|
| T-10-15 (fechamento duplicado pelas duas instancias) | mitigate | `TestFechamentoDaLista::test_a_segunda_instancia_do_usuario_nao_fecha_de_novo` |
| T-10-16 (mensagem a cada tick dentro da janela de 5 min) | mitigate | `TestPresencaNoTick::test_dois_ticks_dentro_da_janela_fecham_uma_vez_so` e `TestFechamentoComOJogoFechado::test_duas_voltas_do_laco_fecham_uma_vez_so` |
| T-10-17 (lista anunciada em conversa errada) | mitigate | `TestPresencaNoTick::test_o_console_recebe_o_texto_CRU_e_o_whatsapp_a_moldura` afirma `conversa is None` |
| T-10-SC (instalacao de pacote) | mitigate | `git diff --stat` cobre 5 arquivos, nenhum de dependencia |

## Known Stubs

| Stub | Arquivo | Linha | Razao / quem resolve |
|---|---|---|---|
| `texto_de_fechamento(..., sugestao=None)` nasce declarado e nenhum chamador o preenche | `l2scanner/presenca.py` | ~`def texto_de_fechamento` | **Intencional e planejado.** O plano 10-04 o cria e o plano 10-05 (D-13, "a lista SUGERE ao loot") e o unico que pode encostar no `loot.py` para preenche-lo. O precedente literal e `EventoAgendado.silenciar_minutos`, que nasceu ignorado na Fase 6 para a Fase 7 usar sem o usuario reeditar o config. O parametro tem dois testes proprios (`test_sugestao_none_nao_acrescenta_nada` e `test_sugestao_preenchida_entra_no_fim`), entao o comportamento dos dois estados esta fixado antes de existir chamador. **Nao bloqueia o objetivo deste plano:** PRES-12 e a lista fechar e ser anunciada, e isso esta completo. |

Nenhum outro stub: nenhum valor vazio codificado, nenhum "TODO"/"FIXME"/"placeholder" novo, nenhum teste com `skip`.

## Self-Check: PASSED

- `l2scanner/presenca.py` — FOUND (`Fechamento`, `fechar_ocorrencias`, `texto_de_fechamento`, `ocorrencias_na_janela` presentes)
- `l2scanner/sessao.py` — FOUND (`presencas_fechadas`, `membros`, o bloco de fechamento presentes)
- `l2scanner/__main__.py` — FOUND (`_fechar_listas_de_presenca` definida e chamada em `laco_da_agenda`; `membros=` na `Sessao`)
- `tests/test_presenca.py` — FOUND (`TestFechamentoDaLista`, `TestTextoDeFechamento`, `TestFechamentoComOJogoFechado`)
- `tests/test_sessao.py` — FOUND (`TestPresencaNoTick`)
- Commits `ca684d8`, `649e6db`, `1d067c2`, `289dfc1`, `a1afcb1` — FOUND em `git log`
- `python -m pytest tests/ -q` -> **976 passed, 2 skipped**
- `python -m ruff check` sobre os tres arquivos de producao -> **All checks passed**
