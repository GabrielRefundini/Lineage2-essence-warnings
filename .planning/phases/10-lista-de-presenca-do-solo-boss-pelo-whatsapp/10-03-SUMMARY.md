---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 03
subsystem: presenca
tags: [presenca, agenda, disco, poda, atomicidade, whatsapp, ast]

# Dependency graph
requires:
  - phase: 10-01
    provides: "`MensagemDeComando.nick` vindo do mapa `[[membro]]` — o nick que entra na lista, nunca o `sender.name`"
  - phase: 10-02
    provides: "`chamar_minutos_antes` no `[[evento]]` — o campo que `ocorrencia_da_chamada` usa como unico criterio"
  - phase: 06-agenda-de-eventos
    provides: "`RegistroEmDisco` com `O_CREAT|O_EXCL`, `chave_da_ocorrencia`, `TOLERANCIA_MINUTOS` e a poda de 3 dias"
  - phase: 08-loot-do-solo-boss
    provides: "`apelido`/`exibir`, o tri-estado do `RegistroDeLoot._criar` e a restricao 'loot nunca importa comandos'"
provides:
  - "`agenda.PREFIXO_PRESENCA` / `PREFIXO_FECHADO` — dois namespaces novos no `.agenda/`"
  - "`agenda._PREFIXOS_CONHECIDOS` — a poda passa a desmontar QUALQUER prefixo conhecido (defeito consertado)"
  - "`RegistroEmDisco.entrar` (tri-estado), `.sair`, `.presentes`, `.fechar`"
  - "`l2scanner/presenca.py` — a decisao do `.join`/`.leave`, pura e sem relogio"
  - "`presenca.RespostaDePresenca(privado, grupo|None)` — o par de redacoes que o plano 10-03b despacha"
  - "`ocorrencia_da_chamada` / `ocorrencia_recem_fechada` / `nomes_dos_membros`"
  - "Portoes de AST: direcao de importacao e ausencia de relogio proprio, o segundo parametrizado sobre TRES modulos"
affects:
  - 10-03b-o-despacho-dos-ramos-join-e-leave
  - 10-04-fechamento-da-lista
  - 10-05-a-lista-sugere-a-vez-do-loot

# Actuals (#2632) — pareia com o `estimate` do plano para calibrar estimativas futuras.
# Base: chars/4 sobre o DIFF realizado (58.791 chars), a MESMA escala do plano.
# O plano estimou raw_tokens 32000 / tokens 64000 e o diff real deu ~14.7k.
# Superestimativa de ~4.3x — a TERCEIRA seguida na mesma direcao (10-01 ~3x,
# 10-02 ~4.5x). Tres fases errando para o mesmo lado, com a razao subindo
# conforme a fatia de teste cresce, e o dado util: o estimador desta fase esta
# contando docstring e teste como se fossem codigo de decisao.
actuals:
  tokens: 14698
  tasks: 2
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tupla de prefixos conhecidos desmontada em laco antes de ler a data — um namespace novo entra ali ou nasce imortal"
    - "Tri-estado escolhido POR CONSEQUENCIA DE PRODUTO, com a docstring nomeando o analogo que NAO serve e por que"
    - "Par de redacoes como TIPO (`privado` + `grupo | None`), com `None` de default para o silencio ser o caminho facil"
    - "Portao de arquitetura por `ast.parse`, nunca por grep, quando a propria docstring cita os nomes proibidos"
    - "Gate de disciplina PARAMETRIZADO sobre todos os modulos que ela cobre, com a mensagem de falha nomeando o modulo"
    - "Borda de tolerancia que derrubou um teste vira um teste proprio em vez de sumir na correcao"

key-files:
  created:
    - l2scanner/presenca.py
    - tests/test_presenca.py
  modified:
    - l2scanner/agenda.py
    - tests/test_agenda.py

key-decisions:
  - "A poda passou a desmontar `_PREFIXOS_CONHECIDOS` num laco: retirar so `cancelado_` fazia todo marcador de outro namespace cair no `except` de `date.fromisoformat` e ficar em disco PARA SEMPRE — o oposto exato do D-11"
  - "`entrar` e tri-estado como o `RegistroDeLoot._criar`, e nao booleano como o `marcar`: `ja_existia` e informacao de PRODUTO (o D-08 depende dela) e `falhou` nunca pode virar anuncio no grupo"
  - "`fechar` E sobre o `marcar`, ao contrario do `entrar` — o fechamento e um ANUNCIO, e para anuncio a regra do projeto e preferir o duplicado ao perdido"
  - "`presentes` compara a chave INTEIRA e nao por `startswith`: o boss das 20:00 e o das 22:00 compartilham quase todo o prefixo do nome de arquivo"
  - "`ocorrencia_recem_fechada` decide pela JANELA DE TEMPO e nao pelo marcador `fechado_` — amarrar a recusa ao marcador faria a resposta depender de o tick ter rodado"
  - "`esta_fechada` NAO foi criado, como o plano determinou por escrito: sem consumidor, e um convite para virar a checagem anterior que a docstring do `marcar` proibe"
  - "`nomes_dos_membros` aceita qualquer iteravel de objetos com `.nick` em vez de `list[Membro]`, para nao importar `comandos` e fechar ciclo"
  - "Os marcadores `comando_<id>` continuam sem poda — registrado em comentario e em teste, NAO consertado: eles nao tem data no nome e resolve-los pede um segundo criterio de idade"

patterns-established:
  - "Um teste de poda POR PREFIXO, parametrizado, para um laco quebrado em um dos namespaces dizer QUAL"
  - "Guarda contra prova vazia em todo portao derivado: o gate de importacao afirma tambem o que presenca.py DEVE importar; o gate de relogio prova que o detector acha um `datetime.now()` literal"
  - "Mutacao deliberada antes de confiar no gate: um `datetime.now()` foi enfiado em presenca.py e o teste caiu nomeando o modulo, depois revertido com `diff` confirmando a volta"

requirements-completed: [PRES-07, PRES-10, PRES-11, PRES-13, PRES-15]

coverage:
  - id: D1
    description: "Dezesseis threads competindo pelo mesmo `.join` produzem exatamente uma confirmacao de grupo"
    requirement: "PRES-10"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestRegistroEmDisco::test_competicao_de_verdade_com_threads_no_entrar"
        status: pass
      - kind: unit
        ref: "tests/test_agenda.py#TestListaDePresencaEmDisco::test_duas_instancias_no_mesmo_instante_so_uma_cria"
        status: pass
    human_judgment: false
  - id: D2
    description: "Um marcador de presenca de quatro dias atras e podado; um de hoje sobrevive — e o mesmo vale para cada prefixo conhecido"
    requirement: "PRES-11"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestPodaAlcancaTodosOsPrefixos::test_o_velho_morre_e_o_de_hoje_sobrevive (4 casos parametrizados)"
        status: pass
      - kind: integration
        ref: "tests/test_agenda.py#TestPodaAlcancaTodosOsPrefixos::test_a_poda_do_arranque_ja_limpa_presenca_velha"
        status: pass
    human_judgment: false
  - id: D3
    description: "A resposta do `.join` diz QUAL horario pegou, mesmo dado tres horas antes, e em TODOS os ramos"
    requirement: "PRES-07"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestJoin::test_join_tres_horas_antes_cita_o_horario_que_pegou"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestFormaDoTexto::test_toda_resposta_com_alvo_cita_o_horario"
        status: pass
    human_judgment: false
  - id: D4
    description: "`.leave` depois do fechamento e recusado dizendo que o boss ja comecou; quem NAO estava na lista fechada opera na proxima ocorrencia"
    requirement: "PRES-13"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestLeave::test_depois_do_fechamento_o_leave_e_RECUSADO"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestLeave::test_quem_NAO_estava_na_lista_fechada_opera_na_proxima"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestOcorrenciaRecemFechada (6 testes, incluindo a virada da meia-noite e a borda da tolerancia)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Toda resposta que nao gravou nada em disco sai com `grupo is None` — nada e anunciado sem ter sido gravado"
    requirement: "PRES-15"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestJoin::test_disco_falhando_NAO_anuncia_no_grupo"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestJoin::test_join_repetido_responde_no_privado_e_CALA_no_grupo"
        status: pass
    human_judgment: false
  - id: D6
    description: "A direcao `presenca -> loot -> agenda` nao fechou ciclo, afirmada por AST e pelo import real"
    requirement: "PRES-15"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDirecaoDeImportacao (5 testes)"
        status: pass
      - kind: integration
        ref: "python -c 'import l2scanner.presenca, l2scanner.loot, l2scanner.__main__'"
        status: pass
    human_judgment: false
  - id: D7
    description: "Nenhum dos tres modulos (`agenda`, `loot`, `presenca`) tem relogio proprio — o tempo entra por parametro"
    requirement: "PRES-15"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_nenhum_now_de_datetime_na_arvore (3 casos parametrizados)"
        status: pass
    human_judgment: false
  - id: D8
    description: "As duas redacoes (privado e grupo) sao efetivamente diferentes e nenhum texto tem acento ou quebra de linha"
    requirement: "PRES-07"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestFormaDoTexto (5 testes sobre 13 frases coletadas)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestJoin::test_as_duas_redacoes_sao_DIFERENTES"
        status: pass
    human_judgment: false
  - id: D9
    description: "A redacao das mensagens do `.join`/`.leave` e clara e util para um party-mate que so ve o WhatsApp"
    verification: []
    human_judgment: true
    rationale: "Se 'Anotado. Voce esta na lista do Solo Boss das 20:00.' e a frase certa para quem digitou, e se a confirmacao de grupo diz o suficiente sem virar ruido, nao e verificavel por teste — so lendo e julgando. Os testes garantem a ESTRUTURA (nick presente, horario presente, sem acento, sem quebra de linha), nunca a qualidade da frase."

# Metrics
duration: 40min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 03: A lista de presenca em disco e a decisao do `.join` Summary

**A lista de presenca ganhou casa no `.agenda/` com atomicidade entre as duas instancias de graca, a poda de 3 dias deixou de ignorar todo namespace que nao fosse `cancelado_`, e o `.join`/`.leave` passaram a ter decisao e DUAS redacoes — uma para quem digitou, outra para o grupo — sem nunca anunciar o que o disco nao gravou.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 de 2
- **Files created:** 2 | **modified:** 2
- **Suite:** 836 -> **909 passed, 2 skipped** (73 testes novos, nenhum afrouxado)

## Accomplishments

- **O defeito de poda era real e foi consertado com teste por prefixo.** `podar` retirava UM prefixo antes de `date.fromisoformat`; `presenca_2026-08-20_solo-boss-2000_j4guar` caia no `except` e ficava em disco para sempre. A prova disso esta no proprio commit RED: os casos parametrizados `[presenca]` e `[fechado]` falharam enquanto `[cancelado]` e `[aviso-sem-prefixo]` passaram — o teste isolou o defeito antes de o codigo mudar.
- **A atomicidade nao foi reimplementada, foi herdada.** `entrar` e `os.O_CREAT | os.O_EXCL | os.O_WRONLY` na mesma pasta que ja resolvia restart e duas instancias. Dezesseis threads competindo pelo mesmo par (chave, slug) produzem exatamente um `"criado"`, com a mensagem de falha dizendo quantas confirmacoes o grupo receberia.
- **O tri-estado e uma decisao de produto, e a docstring diz qual analogo NAO serve.** `ja_existia` e o que faz o `.join` repetido calar no grupo (D-08); `falhou` nunca vira sucesso, porque anunciar uma entrada nao gravada faria a lista fechar sem essa pessoa (T-10-13). O `marcar`, que colapsa `OSError` em `True`, esta citado por escrito como o analogo errado para este caso e certo para o `fechar`.
- **`RespostaDePresenca` existe como TIPO, e nao como convencao.** `grupo is None` e o silencio estruturado; a string vazia seria enviada pelo despachante e viraria bolha em branco. `None` e o default para o silencio no grupo ser o caminho facil.
- **Os portoes de arquitetura usam AST e foram testados contra mutacao.** A direcao `presenca -> loot -> agenda` e a ausencia de relogio proprio sao lidas de `ast.parse`, nunca de grep — as docstrings dos tres modulos citam `comandos`, `sessao` e `datetime.now()` de proposito, para explicar as restricoes, e um grep daria positivo justamente na documentacao que as protege.
- **Zero dependencia nova e zero toque no despacho.** `git diff --stat` cobre exatamente quatro arquivos; `l2scanner/__main__.py` nao foi tocado, porque os ramos `Comando.JOIN`/`LEAVE` sao do plano 10-03b.

## Task Commits

1. **Tarefa 1 RED: a lista em disco e a poda que nao a alcanca** — `469a862` (test)
2. **Tarefa 1 GREEN: `entrar`/`sair`/`presentes`/`fechar` + `_PREFIXOS_CONHECIDOS`** — `b4f6da2` (feat)
3. **Tarefa 2 RED: as duas redacoes e os portoes de AST** — `5a47f32` (test)
4. **Tarefa 2 GREEN: `l2scanner/presenca.py`** — `98451a0` (feat)

## Files Created/Modified

- **`l2scanner/agenda.py`** — `PREFIXO_PRESENCA`, `PREFIXO_FECHADO`, `_PREFIXOS_CONHECIDOS`, os quatro metodos novos do `RegistroEmDisco` e o laco de prefixos na `podar`. Nenhuma assinatura existente mudou.
- **`l2scanner/presenca.py`** (novo) — `RespostaDePresenca`, `ocorrencia_da_chamada`, `ocorrencia_recem_fechada`, `responder_join`, `responder_leave`, `nomes_dos_membros`, mais os dois helpers de recusa (`_sem_nick`, `_sem_chamada_na_agenda`).
- **`tests/test_agenda.py`** — `TestListaDePresencaEmDisco` (13 testes), `TestPodaAlcancaTodosOsPrefixos` (7, dos quais 4 parametrizados) e o teste de threads dentro de `TestRegistroEmDisco`.
- **`tests/test_presenca.py`** (novo) — 52 testes em 9 classes.

## Decisions Made

- **A poda ganhou um laco, e nao um segundo `if`.** Um `if` por prefixo funcionaria hoje e falharia no proximo namespace, que e exatamente como o defeito nasceu. A tupla nomeada e o lugar obvio para o proximo prefixo entrar, e o comentario ao lado diz o que acontece com quem esquecer de po-lo la.
- **`comando_<id>` foi REGISTRADO e nao consertado.** Ele tambem nunca e podado, mas por outro motivo: nao ha data nenhuma no nome. Resolve-lo pede um segundo criterio de idade (mtime, ou id monotonico), que e outro desenho. O fato esta em comentario no codigo e afirmado em `test_arquivo_sem_prefixo_conhecido_continua_intocado`, para nao virar descoberta de novo daqui a tres fases.
- **`esta_fechada` continua nao existindo**, com as duas razoes do plano preservadas na docstring de `ocorrencia_recem_fechada`: a janela de tempo recusa certo mesmo quando o tick nao rodou, e um `esta_fechada` ao lado do `fechar` seria convertido, mais cedo ou mais tarde, na checagem anterior que a docstring do `marcar` proibe por escrito.
- **`nomes_dos_membros` pede a FORMA, nao o tipo.** `Iterable[object]` com `.nick` em vez de `list[Membro]` — a alternativa seria `from .comandos import Membro`, que fecharia o ciclo que o resto do plano gastou testes para impedir.
- **A borda que derrubou um teste virou teste.** A primeira versao do teste de meia-noite usava um boss as 23:50 contra `agora` as 00:02 e falhou — corretamente, porque sao doze minutos e a tolerancia e cinco. Em vez de so ajustar o horario, ficaram os dois: 23:59 (dentro) e 23:50 (fora), com a docstring do segundo dizendo de onde ele veio.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Travessao (`—`) nas mensagens que vao para o WhatsApp**

- **Found during:** Tarefa 2, no primeiro GREEN
- **Issue:** Duas frases de usuario final (a recusa do D-14 e o ramo `"falhou"`) foram escritas com travessao, copiando o tom das docstrings. `test_nenhuma_frase_tem_acento` pegou: `ord("—") == 8212`, muito acima de 127. A convencao do projeto e "portugues SEM acento no texto de usuario", e um caractere fora do ASCII no meio da frase e o mesmo problema pela mesma razao — ele depende da codificacao sobreviver ate o WhatsApp.
- **Fix:** `... das {hora} — deu erro de disco` virou `... das {hora}: deu erro de disco`, e `lista fechou — nao da mais para sair` virou `lista fechou. Nao da mais para sair`. As docstrings mantiveram o travessao: elas nao saem do repositorio.
- **Files modified:** `l2scanner/presenca.py`
- **Committed in:** `98451a0`

**2. [Rule 1 - Bug] O teste da virada de meia-noite afirmava algo falso**

- **Found during:** Tarefa 2, no primeiro GREEN
- **Issue:** O teste esperava que um boss as 23:50 ainda estivesse "recem-fechado" as 00:02 do dia seguinte. Sao doze minutos, e `TOLERANCIA_MINUTOS` e cinco — a expectativa estava errada, nao o codigo. Aceita-la teria exigido afrouxar a tolerancia, que e a mesma propriedade do laco usada por todos os avisos.
- **Fix:** O teste passou a usar 23:59 (dois minutos, dentro da janela, e ainda assim do outro lado da meia-noite — que e a propriedade que ele existe para provar) e ganhou um IRMAO, `test_doze_minutos_depois_do_alvo_ja_passou_da_tolerancia`, afirmando o `None` do caso original. A borda ficou registrada em vez de apagada na correcao.
- **Files modified:** `tests/test_presenca.py`
- **Committed in:** `98451a0`

---

**Total deviations:** 2 auto-fixed, ambas bugs pegos pelos proprios testes novos antes de qualquer commit GREEN. Nenhuma mudanca de escopo, nenhuma assinatura alterada em relacao ao `<interface_context>` do plano.

## Issues Encountered

- **O gate do relogio foi mutado antes de ser aceito.** Um `def _mutacao_temporaria(): return datetime.now()` foi acrescentado ao fim de `presenca.py`; `test_nenhum_now_de_datetime_na_arvore[presenca.py]` caiu com `presenca.py tem relogio proprio: ['datetime.now']` — a mensagem nomeia o modulo, como o criterio de aceite exigia. A mutacao foi revertida e `diff` contra a copia pre-mutacao confirmou o arquivo identico antes do commit. Sem esse passo, um filtro AST escrito com um `and` a mais passaria sem provar nada.
- **`date.today()` esta FORA da proibicao do gate de relogio, e a excecao esta escrita.** O unico uso e o default de `podar(hoje=None)`, um parametro que todos os testes passam. Incluir `today` no conjunto proibido derrubaria `agenda.py` por um default que a disciplina nunca quis proibir — a regra e "o instante da DECISAO vem de fora". A docstring da classe de teste diz isso, para o proximo leitor nao "consertar" o gate.
- **Ruff continua acusando erros pre-existentes em outros arquivos de teste** (imports nao usados, sobretudo), como o plano 10-01 ja havia registrado. `ruff check` sobre os quatro arquivos desta fase passa limpo. Fora do escopo por regra; nao foram tocados.

## Known Stubs

Nenhum stub. Duas ausencias INTENCIONAIS, ambas escritas no plano:

1. Os ramos `Comando.JOIN` / `Comando.LEAVE` continuam caindo no `else: continue` de `atender_comandos` — `l2scanner/__main__.py` nao foi tocado de proposito. Ligar `RespostaDePresenca` ao despacho, e generalizar o bloco que hoje serve os oito ramos antigos, e o plano **10-03b**, separado porque aquela mudanca toca um arquivo com 19-20% de cobertura.
2. `RegistroEmDisco.fechar` existe e esta testado, mas ninguem o chama ainda: quem dispara o fechamento no horario do boss e o plano **10-04**. `PREFIXO_FECHADO` ja e conhecido pela poda desde agora, entao nenhum marcador escrito depois nascera imortal.

Efeito colateral herdado do plano 10-01 e ainda valendo: um `.join` mandado hoje e marcado como obedecido em `.agenda/` e nao produz resposta nenhuma. Nao ha estado corrompido — so silencio, ate 10-03b.

## Threat Flags

Nenhuma superficie de seguranca nova fora do `<threat_model>` do plano. As mitigacoes previstas foram aplicadas:

| Threat ID | Disposition | Onde ficou |
|---|---|---|
| T-10-04 (tampering nos marcadores) | aceito, como planejado | Arquivo vazio, sem estatistica derivada, agora efetivamente podado em 3 dias |
| T-10-11 (`.join` em laco enchendo o grupo) | mitigado | Tri-estado `ja_existia` cala no grupo; `test_join_repetido_responde_no_privado_e_CALA_no_grupo` |
| T-10-12 (travessia de caminho pelo nick) | mitigado | `test_o_slug_com_separador_de_caminho_nao_escapa_da_pasta` prova a segunda barreira (`apelido`); a primeira (`NICK_VALIDO`) ja e do plano 10-01 |
| T-10-13 (anunciar o que nao foi gravado) | mitigado | `"falhou"` nunca colapsa em sucesso; `test_disco_falhando_NAO_anuncia_no_grupo` |
| T-10-14 (marcadores acumulando) | mitigado | `_PREFIXOS_CONHECIDOS` + `TestPodaAlcancaTodosOsPrefixos`, um caso por prefixo |
| T-10-SC (instalacao de pacote) | mitigado | Zero dependencia nova; `presenca.py` usa so stdlib e modulos do pacote |

## User Setup Required

Nenhuma. O `chamar_minutos_antes = 110` do Solo Boss ja entrou no `config.toml` no plano 10-02, e os blocos `[[membro]]` continuam sendo a unica coisa que o usuario precisa preencher — decisao do plano 10-01, inalterada aqui.

## Next Phase Readiness

Pronto para 10-03b, 10-04 e 10-05. O que eles herdam:

- **10-03b** recebe `responder_join`/`responder_leave` prontos, devolvendo o par. O trabalho la e o despacho: `resposta.privado` para a conversa de origem, `resposta.grupo` para `CHATWOOT_CONVERSAS` quando nao for `None`.
- **10-04** recebe `fechar` (atomico, um anuncio por ocorrencia entre as duas instancias), `presentes` e `nomes_dos_membros` — os tres pedacos da lista final com a grafia do `config.toml`.
- **10-05** recebe `presentes(chave)` para sugerir a vez entre quem esta na lista. A leitura acontece na BORDA e o resultado entra em `loot.py` por parametro; `test_loot_nunca_importa_presenca` falha se alguem tentar o atalho.

Sem blockers.

## Self-Check: PASSED

- Arquivos afirmados existem: `l2scanner/presenca.py`, `l2scanner/agenda.py`, `tests/test_presenca.py`, `tests/test_agenda.py`.
- Commits afirmados existem: `469a862`, `b4f6da2`, `5a47f32`, `98451a0`.
- `python -m pytest tests/ -q` -> **909 passed, 2 skipped** (linha de base 836; os 2 skips sao pre-existentes).
- `python -c "import l2scanner.presenca, l2scanner.loot, l2scanner.__main__"` -> ok, sem ciclo.
- `python -m ruff check` sobre os quatro arquivos desta fase -> limpo.
- `git diff --stat` contra a base cobre exatamente 4 arquivos; nenhum arquivo de dependencia e nenhum toque em `l2scanner/__main__.py`.
- `STATE.md` e `ROADMAP.md` NAO foram modificados — o orquestrador e o dono dessas escritas.

---
*Phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp*
*Completed: 2026-08-26*
