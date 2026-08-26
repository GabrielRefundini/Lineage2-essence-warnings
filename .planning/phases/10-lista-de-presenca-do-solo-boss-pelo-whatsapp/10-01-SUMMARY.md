---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 01
subsystem: auth
tags: [autorizacao, whatsapp, chatwoot, toml, comandos, presenca]

# Dependency graph
requires:
  - phase: 08-loot-do-solo-boss
    provides: "Comando.LOOT_* e o `.loot/` que nunca e podado — a estatistica que o nivel de membro NAO pode alcancar"
  - phase: quick-260825-t1n
    provides: "`_AJUDA` derivada do enum + os tripwires `set(Comando) == set(_AJUDA)` e a ordem das familias"
provides:
  - "Autorizacao de comando em DOIS NIVEIS: dono (aditivo, alcanca tudo) e membro (so `COMANDOS_DE_MEMBRO`)"
  - "`Comando.JOIN` e `Comando.LEAVE` reconhecidos pelo caminho real de leitura (o que eles FAZEM e o plano 10-03)"
  - "`comandos.Membro`, `nick_do_membro`, `autorizado_para`, `colisoes_de_telefone`, `COMANDOS_DE_MEMBRO`"
  - "`MensagemDeComando.nick` — o nick do JOGO, vindo do mapa `[[membro]]` e nunca do `sender.name`"
  - "`config.ler_membros` lendo blocos `[[membro]]` do config.toml"
  - "Aviso alto no arranque quando dois telefones configurados colidem nos 8 digitos finais"
affects:
  - 10-02-chamada-na-agenda
  - 10-03-join-leave-que-fazem-alguma-coisa
  - 10-04-lista-em-disco
  - 10-05-fechamento-e-loot

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Base: chars/4 sobre o DIFF realizado (48.778 chars). Nao arredondado para
# perto da estimativa: o plano estimou raw_tokens 39000 / tokens 78000, e o
# diff real deu ~12.2k. A superestimativa de ~3x e o dado util aqui.
actuals:
  tokens: 12195
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Autorizacao em dois niveis, com o nivel antigo avaliado PRIMEIRO e ADITIVO"
    - "Lista de alcance por INCLUSAO (`COMANDOS_DE_MEMBRO`), nunca por exclusao"
    - "Tripwire de teste DERIVADO do enum (`set(Comando) - COMANDOS_DE_MEMBRO`) com guarda contra prova vazia"
    - "Identidade por arquivo editado a mao (config.toml) vs segredo por .env — assimetria proposital e comentada"

key-files:
  created: []
  modified:
    - l2scanner/comandos.py
    - l2scanner/config.py
    - l2scanner/__main__.py
    - config.toml
    - tests/test_comandos.py

key-decisions:
  - "O nivel de dono e avaliado antes do de membro e continua alcancando TODO comando do enum — o nivel novo ACRESCENTA gente, nunca tira"
  - "`COMANDOS_DE_MEMBRO` e lista de inclusao: um comando novo no enum nasce FORA do alcance de membro sem ninguem precisar lembrar de exclui-lo"
  - "`.join`/`.leave` entram no `_VOCABULARIO` fixo (nao em `interpretar_dinamico`), pagando o preco ja aceito de tirar 4 palavras do espaco de nicks consultaveis"
  - "`Membro` nasce em `comandos.py` e nao em `config.py`, para nao fechar o ciclo `config -> comandos -> config`"
  - "`ler_membros` reusa `AgendaInvalida` em vez de criar excecao nova — ela ja E a excecao de 'o config.toml nao faz sentido'"
  - "Colisao de 8 digitos avisa alto mas NAO derruba o scanner: entre dois membros ela nao escala privilegio nenhum"
  - "O nono digito brasileiro (`+5544997077000` vs `554497077000`) e a MESMA pessoa e nao conta como colisao — gritar ali treinaria o usuario a ignorar o aviso"

patterns-established:
  - "Fronteira de autorizacao provada nos dois sentidos: o que o nivel alcanca E o que ele recusa, com a recusa derivada do enum"
  - "Guarda contra prova vazia: um tripwire derivado precisa afirmar que o conjunto derivado nao ficou vazio, nomeando os itens perigosos"
  - "Estado de permissao nunca e descoberto por acidente: o arranque nomeia quem ganhou o nivel novo, como o aviso COMANDOS ABERTOS ja fazia"

requirements-completed: [PRES-03, PRES-04]

coverage:
  - id: D1
    description: "Um telefone declarado em `[[membro]]` manda `.join` e o pedido atravessa as cinco travas, chegando com o nick do mapa"
    requirement: "PRES-03"
    verification:
      - kind: integration
        ref: "tests/test_comandos.py#TestMembroNoConfigToml::test_o_telefone_do_arquivo_atravessa_o_join"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestFronteiraDeAutorizacao::test_o_membro_ALCANCA_o_que_e_dele_e_chega_com_o_nick"
        status: pass
    human_judgment: false
  - id: D2
    description: "Esse mesmo telefone e RECUSADO em todo comando fora de `COMANDOS_DE_MEMBRO`, com a lista de recusa derivada do enum"
    requirement: "PRES-04"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestFronteiraDeAutorizacao::test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestMembroNoConfigToml::test_o_mesmo_telefone_PARA_no_corrigir"
        status: pass
    human_judgment: false
  - id: D3
    description: "Um telefone de CHATWOOT_TELEFONES_COMANDO continua alcancando TODOS os comandos, inclusive `.join` e `.leave` — o nivel de membro e aditivo"
    requirement: "PRES-04"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestFronteiraDeAutorizacao::test_o_DONO_continua_alcancando_TODO_comando"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestAjuda::test_toda_sintaxe_anunciada_volta_como_o_comando_certo"
        status: pass
    human_judgment: false
  - id: D4
    description: "O nick que acompanha o pedido vem do mapa `[[membro]]`, nunca de `sender.name` do Chatwoot"
    requirement: "PRES-03"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestFronteiraDeAutorizacao::test_o_dono_que_nao_e_membro_chega_sem_nick"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestMembroNoConfigToml::test_o_telefone_do_arquivo_atravessa_o_join"
        status: pass
    human_judgment: false
  - id: D5
    description: "Dois telefones configurados com os mesmos 8 digitos finais viram aviso alto no arranque, nomeando os dois e dizendo a consequencia"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestColisaoDeTelefone (6 testes)"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestArranqueComMembros::test_a_colisao_dono_contra_membro_GRITA_nomeando_os_dois"
        status: pass
    human_judgment: false
  - id: D6
    description: "O config.toml do repositorio nao carrega telefone nenhum — so exemplo comentado"
    verification:
      - kind: integration
        ref: "tests/test_comandos.py#TestMembroNoConfigToml::test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem"
        status: pass
    human_judgment: false
  - id: D7
    description: "O bloco `[[membro]]` do config.toml e legivel e suficiente para um nao-programador preencher sem ajuda"
    verification: []
    human_judgment: true
    rationale: "A qualidade do texto de configuracao para um nao-programador nao e verificavel por teste — so lendo o arquivo e julgando se as duas frases sobre o que o nivel alcanca e o que ele nao alcanca sao claras."

# Metrics
duration: 35min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 01: Autorizacao em dois niveis Summary

**A autorizacao de comando deixou de ser global e binaria: `[[membro]]` no config.toml da a um party-mate acesso a `.join`/`.leave` e a NADA mais, enquanto `CHATWOOT_TELEFONES_COMANDO` continua alcancando o enum inteiro — com a lista de recusa derivada do enum e a colisao de 8 digitos gritando no arranque.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-26T11:32-03:00 (aprox.)
- **Completed:** 2026-08-26T12:06:12-03:00
- **Tasks:** 3 de 3
- **Files modified:** 5

## Accomplishments

- **A fronteira existe e e aditiva.** `autorizado_para(comando, remetente, telefones, membros)` pergunta pelo nivel de dono PRIMEIRO e devolve `True` na hora se ele aceitar. So depois, e so para o que estiver em `COMANDOS_DE_MEMBRO`, consulta o mapa `[[membro]]`. Nenhum party-mate ganha `.corrigir` nem `.pegou` de carona.
- **A recusa e derivada, nao digitada.** O teste da fronteira computa `set(Comando) - COMANDOS_DE_MEMBRO` dentro do proprio teste, com uma guarda que afirma que `LOOT_CORRIGIR` e `LOOT_ATRIBUIR` continuam no conjunto derivado. Um comando novo no enum entra nessa prova sozinho.
- **`.join` e `.leave` ja atravessam o caminho real de leitura**, com linha na ajuda (familia `Presenca`, entre `Silencio` e `Loot do Solo Boss`) e vocabulario fixo. O que eles FAZEM fica para o plano 10-03 — hoje caem no `else: continue` do despacho.
- **A colisao de 8 digitos deixou de ser invisivel.** `colisoes_de_telefone` compara dono-contra-dono, membro-contra-membro e dono-contra-membro, e o arranque nomeia as duas entradas COMO FORAM CONFIGURADAS e diz a consequencia. O nono digito brasileiro nao conta como colisao.
- **Zero dependencia nova.** `git diff --stat` nao toca `requirements.txt`, `pyproject.toml` nem qualquer arquivo de dependencia; todo import novo e stdlib (`collections.abc.Sequence`) ou intra-pacote.
- **Suite de 785 -> 811 testes**, sem nenhum teste afrouxado.

## Task Commits

1. **Tarefa 1 (tracer): Um telefone de membro atravessa `.join` e para em tudo o mais** — `68e7573` (feat)
2. **Tarefa 2: A fronteira provada nos dois sentidos, com tripwire** — `de05321` (test)
3. **Tarefa 3: A colisao de 8 digitos deixa de ser invisivel** — `520cade` (feat)

## Files Created/Modified

- `l2scanner/comandos.py` — `Membro`, `Comando.JOIN`/`LEAVE`, `COMANDOS_DE_MEMBRO`, `nick_do_membro`, `autorizado_para`, `colisoes_de_telefone`, `MensagemDeComando.nick`, parametro `membros` em `comandos_novos` e `LeitorDeComandos`. A docstring de topo passou a enumerar a QUINTA trava e os seus dois niveis.
- `l2scanner/config.py` — `ler_membros` + `_membro_de_dict`, com a mesma disciplina de `ler_agenda` (ausente nao e erro, mal formado e erro de arranque) e a assimetria `.env` vs `config.toml` comentada.
- `l2scanner/__main__.py` — `montar_leitor_de_comandos` le `ler_membros()`, passa ao leitor, loga quantos party-mates ganharam `.join`/`.leave` e grita cada colisao. A mensagem de "para restringir" passou a citar `[[membro]]`.
- `config.toml` — bloco `[[membro]]` COMENTADO ao fim, dizendo em duas frases o que o nivel alcanca e o que ele nao alcanca. O arquivo versionado nao carrega telefone de ninguem.
- `tests/test_comandos.py` — tres classes novas (`TestFronteiraDeAutorizacao`, `TestColisaoDeTelefone`, `TestArranqueComMembros`, `TestMembroNoConfigToml`), `_FAMILIAS_ESPERADAS` crescida com `Presenca`, e `test_o_vocabulario_e_fechado` crescido com `JOIN`/`LEAVE`.

## Decisions Made

- **A ordem em `autorizado_para` e a decisao inteira.** Dono primeiro, e a docstring diz por escrito que inverter a ordem quebra `test_toda_sintaxe_anunciada_volta_como_o_comando_certo` e que, quando isso acontecer, o teste esta certo e o codigo esta errado.
- **`_forma_canonica` e `_mesma_pessoa` nasceram para responder outra pergunta que `telefone_equivalente`.** Aquela pergunta "estes dois casam pela regra do scanner?"; estas perguntam "estes dois sao a mesma pessoa escrita de dois jeitos?". Sem essa separacao, `+5544997077000` e `554497077000` — a configuracao mais provavel do mundo, porque a base do WhatsApp carrega as duas formas — viraria um aviso falso no arranque, e um aviso que grita a toa e um aviso que o usuario aprende a ignorar.
- **A colisao avisa mas nao derruba.** Recusar a subir por causa de uma colisao entre dois membros — que nao escala privilegio nenhum — deixaria o usuario sem vigia por um erro de digitacao.
- **Apelidos curtos de proposito.** `.entrar`/`.sair` e `.join`/`.leave`, e so. Cada palavra no `_VOCABULARIO` e um personagem que deixa de ser consultavel por `.<nick>` — o mesmo preco que `_PALAVRAS_DE_CANCELAMENTO` ja paga e ja documenta.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_o_vocabulario_e_fechado` era um TERCEIRO tripwire que o plano nao listou**

- **Found during:** Tarefa 1
- **Issue:** O plano nomeou dois tripwires que a fase quebraria de proposito (`set(Comando) == set(_AJUDA)` e `_FAMILIAS_ESPERADAS`). Existe um terceiro, em `tests/test_comandos.py:84`, que afirma `set(Comando) == {…}` com o enum inteiro escrito a mao — ele falhou assim que `JOIN` e `LEAVE` nasceram.
- **Fix:** O conjunto CRESCEU com `Comando.JOIN` e `Comando.LEAVE`, e o comentario ao lado deles explica a natureza nova: sao os dois unicos comandos alcancaveis por um segundo nivel de autorizacao. O teste nao foi afrouxado — continua exigindo que cada membro do enum esteja escrito por extenso com a razao de existir.
- **Files modified:** `tests/test_comandos.py`
- **Verification:** `python -m pytest tests/test_comandos.py -q` — 111 passed no fim da Tarefa 1.
- **Committed in:** `68e7573`

**2. [Rule 2 - Missing Critical] O criterio de aceite do nono digito exigia logica que a assinatura do plano nao previa**

- **Found during:** Tarefa 3
- **Issue:** O plano pediu que `colisoes_de_telefone` usasse `telefone_equivalente` e, ao mesmo tempo, que `+5544997077000` e `554497077000` NAO contassem como colisao. Mas `telefone_equivalente` devolve `True` para esse par — e essa e a configuracao mais provavel de todas, porque a base do WhatsApp carrega as duas formas do mesmo numero. Uma implementacao literal gritaria no arranque de quem nao fez nada errado.
- **Fix:** Duas funcoes privadas novas, `_forma_canonica` (tira o nono digito de um celular BR de 13 digitos) e `_mesma_pessoa` (sufixo, depois da normalizacao). A colisao passa a ser `telefone_equivalente(a, b) and not _mesma_pessoa(a, b)`. `telefone_equivalente` continua sendo a UNICA implementacao do corte de 8 digitos usada para autorizar.
- **Files modified:** `l2scanner/comandos.py`
- **Verification:** `TestColisaoDeTelefone::test_o_nono_digito_NAO_e_colisao` cobre os dois arranjos (dono-dono e dono-membro); os tres tipos de par perigoso continuam sendo achados.
- **Committed in:** `520cade`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Nenhuma mudanca de escopo. A primeira foi um tripwire a mais crescendo junto com o enum, exatamente como os outros dois; a segunda foi a unica forma de satisfazer dois criterios de aceite que se contradiziam na letra.

## Issues Encountered

- **O gate do tracer (Tarefa 1) rodou automatizado em vez de virar checkpoint humano.** O `<verify>` da tarefa e `python -m pytest tests/test_comandos.py -q`, uma verificacao inteiramente automatica sem componente visual, e o `.planning/config.json` tem `human_verify_mode: "end-of-phase"` — a instrucao explicita do usuario de que a verificacao humana acontece no fim da fase. O gate foi satisfeito re-rodando o verify ponta a ponta (111 testes de `test_comandos.py`, 791 na suite inteira) antes de qualquer tarefa de expansao. Registrado aqui para o verificador da fase saber que nenhum humano olhou para isto ainda.
- **O tripwire derivado foi testado contra mutacao, e nao so escrito.** Antes de commitar a Tarefa 2, `COMANDOS_DE_MEMBRO` foi temporariamente alargado para incluir `Comando.LOOT_CORRIGIR`; `test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele` falhou com a mensagem certa, nomeando o comando. A mutacao foi revertida e `git diff --stat l2scanner/comandos.py` confirmou o arquivo de volta ao estado commitado antes de seguir. Sem esse passo, uma prova derivada de conjunto vazio passaria sem provar nada.
- **Ruff acusa 26 erros pre-existentes em outros arquivos de teste** (imports nao usados, sobretudo). Nenhum deles esta nos cinco arquivos desta fase — `ruff check` sobre os arquivos alterados passa limpo. Fora do escopo desta fase por regra (SCOPE BOUNDARY); nao foram tocados.

## Known Stubs

Nenhum stub. `Comando.JOIN` e `Comando.LEAVE` sao reconhecidos mas ainda caem no `else: continue` do despacho em `atender_comandos` — isto e INTENCIONAL e esta escrito no `<objective>` do plano: "ao fim deste plano o `.join` e o `.leave` ja EXISTEM, ja sao reconhecidos pelo caminho real de leitura e ja tem a autorizacao certa — o que eles FAZEM e o plano 10-03". O plano 10-03 fecha isso.

Efeito colateral conhecido e aceito ate la: um `.join` mandado hoje e marcado como obedecido em `.agenda/` (o `registro.marcar` roda antes do despacho) e nao produz resposta nenhuma. Nao ha estado corrompido — so silencio, ate 10-03.

## Threat Flags

Nenhuma superficie de seguranca nova fora do `<threat_model>` do plano. As mitigacoes previstas foram aplicadas:

| Threat ID | Disposition | Onde ficou |
|---|---|---|
| T-10-01 (EoP em `autorizado_para`) | mitigado | Dono avaliado primeiro e aditivo; `COMANDOS_DE_MEMBRO` por inclusao; recusa derivada do enum com guarda contra prova vazia |
| T-10-02 (spoofing pelo corte de 8 digitos) | mitigado | `colisoes_de_telefone` + dois `log.warning` no arranque, nomeando as duas entradas e a consequencia |
| T-10-03 (telefone num config.toml versionado) | mitigado | So exemplo comentado; `test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem` |
| T-10-05 (eco do bot voltando como comando) | mitigado | `test_o_ECO_DO_BOT_nao_vira_comando`, com controle provando que a recusa vem do `message_type` e nao de o texto ser inerte |
| T-10-SC (instalacao de pacote) | mitigado | Zero dependencia nova; todo import novo e stdlib ou intra-pacote |

## User Setup Required

Nenhuma configuracao de servico externo. Para usar o nivel novo, o usuario descomenta os blocos `[[membro]]` no proprio `config.toml` e poe nick + telefone de cada party-mate. Sem isso, o scanner se comporta exatamente como antes desta fase.

## Next Phase Readiness

Pronto para os planos 10-02 a 10-05. O que eles herdam:

- `MensagemDeComando.nick` ja chega preenchido no despacho — o plano 10-03 so precisa dos ramos `elif pedido.comando is Comando.JOIN:` / `LEAVE`, que hoje caem no `else: continue`.
- `leitor.membros` ja reflete o `config.toml`, entao o roster para a lista de presenca ja esta na borda.
- `COMANDOS_DE_MEMBRO` e o unico lugar a mexer se um comando futuro precisar do nivel de membro — e o teste derivado avisa se alguem mexer sem querer.

Sem blockers.

---
*Phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp*
*Completed: 2026-08-26*
