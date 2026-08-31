---
phase: 03-um-aviso-por-nascimento-com-o-chat-mandando-no-alvo
workstream: tiat
plan: 01
subsystem: testing
tags: [marcador-duravel, o-excl, deduplicacao, ast-gate, respawn, agenda]

requires:
  - phase: 01-reconhecimento-do-nascimento
    provides: "VigiaDeBosses, AvisoDeBoss, OrigemDoAviso e o padrao do anuncio do servidor"
  - phase: 02-janela-de-respawn
    provides: "respawn.py, a ancora em disco, chave_do_nascimento, ancora_de_chave e anunciar_janelas"
provides:
  - "PREFIXO_ANUNCIO e RegistroEmDisco.registrar_anuncio: o aviso de nascimento deixou de ser o unico alerta do projeto sem marcador duravel"
  - "A nocao de EPISODIO em respawn.py: MARGEM_DO_EPISODIO, ancoras_do_boss, inicio_do_episodio, chave_do_anuncio, anunciar_nascimento"
  - "ResultadoDoTick.nascimentos_calados mais log.info: todo anuncio suprimido deixa rastro"
  - "tests/test_anuncio_unico.py: os portoes AST da ordem e da posicao da escrita da ancora"
affects: [03-02, mortes-e-comandos, qualquer fase que grave marcador em .agenda/]

actuals:
  tokens: 17538
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Marcador de SUPRESSAO com data e poda: um marcador que cala precisa expirar, porque um silencio imortal nao deixa rastro nenhum"
    - "Chave duravel ancorada no inicio do EPISODIO, e nao no instante da deteccao nem na ancora mais recente"
    - "Portao AST sobre a POSICAO e a ORDEM de uma instrucao, e nao so sobre a existencia da chamada"

key-files:
  created:
    - tests/test_anuncio_unico.py
  modified:
    - l2scanner/agenda.py
    - l2scanner/respawn.py
    - l2scanner/sessao.py
    - tests/test_respawn.py
    - tests/test_sessao.py
    - tests/test_agenda.py

key-decisions:
  - "D-28: a chave do anuncio e `anuncio_<YYYY-MM-DD>_<boss-slug>-<HHMM>` com a data e a hora do INICIO DO EPISODIO. O instante da deteccao daria chaves diferentes nas duas instancias; a ancora mais recente renasceria a cada remarcacao de alvo."
  - "D-29: a janela do episodio e `respawn_horas_min - MARGEM_DO_EPISODIO` (5 min), deliberadamente MAIS CURTA que o minimo do servidor, com limite inferior ESTRITO. Longa demais cala um nascimento real e ninguem percebe; curta demais repete uma mensagem que o usuario ignora."
  - "D-30: o silencio e marcador PROPRIO, e nao derivado da ancora. A ancora e reescrita a cada retarget (D-15), entao um silencio derivado dela renasceria a cada remarcacao, que e metade do defeito de campo."
  - "`registrar_anuncio` nasceu SEM listador irmao (`anuncios()`). A ausencia e a mitigacao de D-21 posta na forma do codigo: o unico uso imaginavel seria conferir antes de falar, que e o read-then-write proibido."
  - "A ancora e escrita ANTES e FORA do `if` do anuncio, e a posicao e afirmada por AST porque com uma instancia so a ordem e indiferente e todo o resto ficaria verde."

patterns-established:
  - "Portao AST de POSICAO: comparar o indice de duas instrucoes dentro do corpo de um `ast.For`, com shell fabricado de ordem invertida provando que o detector morde"
  - "Portao AST de CONTENCAO: nenhum `ast.If` que contenha a chamada A pode conter a chamada B, com shell fabricado provando a acusacao"
  - "Um comportamento aceito ganha teste NOMEADO (`TestOQueASupressaoPERDE`), nunca fica sem cobertura"

requirements-completed: [UNIC-01, UNIC-03, UNIC-04, UNIC-05, UNIC-06, UNIC-07, UNIC-08]

coverage:
  - id: D1
    description: "Duas Sessao sobre a MESMA .agenda/ vendo o mesmo anuncio produzem exatamente UM despacho, e um terceiro processo subindo depois nao reenvia"
    requirement: UNIC-01
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestUmNascimentoUmaMensagem::test_a_SEGUNDA_instancia_sobre_a_mesma_pasta_CALA"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestUmNascimentoUmaMensagem::test_o_REINICIO_nao_reenvia"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestOsElosDaFiacao::test_o_sitio_dos_pixels_nao_decide_por_conta_propria"
        status: pass
    human_judgment: false
  - id: D2
    description: "Com o chat tendo anunciado, remarcar o boss produz ZERO mensagem nova, e as remarcacoes continuam gravando ancora"
    requirement: UNIC-03
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestOAlvoCalaDepoisDeOChatFalar::test_o_chat_anuncia_uma_vez_e_as_remarcacoes_nao_produzem_nada"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestOAlvoCalaDepoisDeOChatFalar::test_as_remarcacoes_CONTINUAM_gravando_ancora"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sem o chat ter falado, o alvo anuncia UMA vez e depois cala: o fallback continua existindo e continua sendo unico"
    requirement: UNIC-04
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestOFallbackDoAlvoContinuaExistindo::test_sem_o_chat_o_alvo_anuncia_UMA_vez"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestOFallbackDoAlvoContinuaExistindo::test_as_remarcacoes_seguintes_calam"
        status: pass
    human_judgment: false
  - id: D4
    description: "O silencio dura ate o proximo nascimento ser POSSIVEL pela regra do [[boss]], e nao mais: um segundo nascimento respawn_horas_min depois AINDA anuncia"
    requirement: UNIC-05
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestOSilencioAcabaQuandoONascimentoVoltaASerPossivel::test_um_segundo_nascimento_em_respawn_horas_min_AINDA_ANUNCIA"
        status: pass
      - kind: unit
        ref: "tests/test_respawn.py#TestOInicioDoEpisodio::test_a_borda_INFERIOR_e_ESTRITA_a_ancora_no_limite_esta_FORA"
        status: pass
    human_judgment: false
  - id: D5
    description: "A ancora continua sendo gravada como hoje, inclusive pelo alvo e inclusive quando o anuncio e suprimido, afirmado por teste E por portao AST sobre a posicao da escrita"
    requirement: UNIC-06
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestAAncoragemSobreviveASupressao::test_a_ancora_do_alvo_existe_em_disco_com_o_anuncio_suprimido"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestAAncoraSobreviveAoSilencio::test_a_ancora_nao_mora_dentro_do_if_do_anuncio"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestAAncoraSobreviveAoSilencio::test_a_ancora_e_escrita_ANTES_de_a_chave_do_anuncio_ser_calculada"
        status: pass
    human_judgment: false
  - id: D6
    description: "PREFIXO_ANUNCIO esta em _PREFIXOS_CONHECIDOS, a poda o alcanca, e o guarda derivado por introspecao continua verde"
    requirement: UNIC-07
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestPodaAlcancaTodosOsPrefixos::test_o_prefixo_do_anuncio_esta_no_balde_dos_podaveis"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestOSilencioExpiraEmVezDeCalarParaSempre::test_um_anuncio_de_quatro_dias_atras_e_apagado"
        status: pass
    human_judgment: false
  - id: D7
    description: "Todo anuncio SUPRIMIDO deixa rastro: entra em resultado.nascimentos_calados e sai no log com o boss e a razao"
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestOAlvoCalaDepoisDeOChatFalar::test_cada_deteccao_calada_deixa_rastro"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestOAlvoCalaDepoisDeOChatFalar::test_o_silencio_sai_no_log_com_o_boss"
        status: pass
    human_judgment: false
  - id: D8
    description: "Tudo acima e demonstravel com o jogo fechado, sem calibracao, sem OCR e sem rede"
    requirement: UNIC-08
    verification:
      - kind: integration
        ref: "python -m pytest -q (2785 passed, 23 skipped, jogo fechado, sem rede)"
        status: pass
    human_judgment: false
  - id: D9
    description: "Em campo, com as duas instancias reais do usuario e ele remarcando o boss, um nascimento produz UMA mensagem no grupo de WhatsApp"
    verification: []
    human_judgment: true
    rationale: "O defeito e de CAMPO e so aparece com duas instancias reais, OCR real e o usuario remarcando o alvo no jogo. A suite prova a mecanica com Sessao construidas em tmp_path; a confirmacao final e o proximo nascimento de Tiat com as duas instancias rodando."

duration: 71min
completed: 2026-08-31
status: complete
---

# Phase 3 Plan 01: Um aviso por nascimento Summary

**O aviso de nascimento ganhou marcador duravel (`anuncio_<data>_<boss>-<HHMM>`, ancorado no inicio do EPISODIO) e passou a decidir por `registrar_anuncio`, com a ancora escrita antes e fora do `if` do anuncio e portoes AST guardando a ordem.**

## Performance

- **Duration:** 71 min
- **Started:** 2026-08-31T01:20:25Z
- **Completed:** 2026-08-31T02:31:18Z
- **Tasks:** 3
- **Files modified:** 7 (1 criado, 6 modificados)

## Accomplishments

- **A causa 1 do defeito de campo esta fechada.** `sessao._processar_bosses` era o unico alerta do projeto que chamava `_despachar` sem passar por `registro.marcar()`. Agora passa, por `respawn.anunciar_nascimento` -> `agenda.registrar_anuncio` -> `marcar`. Duas `Sessao` sobre a mesma `.agenda/` somam UM despacho, e uma terceira construida do zero (o reinicio) soma zero.
- **A nocao de EPISODIO existe e mora num lugar so.** `respawn.py` ganhou `MARGEM_DO_EPISODIO`, `ancoras_do_boss`, `inicio_do_episodio`, `chave_do_anuncio` e `anunciar_nascimento`. A palavra `episodio` foi escolhida porque `janela` ja significa duas coisas neste pacote e `ciclo` uma terceira.
- **A supressao nao virou perda.** Um segundo nascimento exatamente `respawn_horas_min` depois do primeiro AINDA anuncia — a janela do episodio e `respawn_horas_min - 5min`, com limite inferior estrito, e ha teste nomeado para isso e para a borda exata.
- **A ancoragem sobreviveu inteira (D-27).** A ancora e escrita antes e fora do `if` do anuncio, continua sendo gravada pelo alvo, e continua sendo gravada quando o anuncio e calado — afirmado pelo ARQUIVO em disco, pelo `ResultadoDoTick`, e por dois portoes AST com shell fabricado.
- **O silencio deixa rastro.** `ResultadoDoTick.nascimentos_calados` mais uma linha de `log.info` nomeando o boss. Sem eles, o unico sintoma de uma supressao errada seria o silencio (T-03-05).
- **O marcador de silencio expira.** `PREFIXO_ANUNCIO` entrou em `_PREFIXOS_CONHECIDOS`; um marcador de anuncio imortal calaria aquele boss para sempre, sem erro e sem log (T-03-03).

## Task Commits

Cada tarefa foi commitada atomicamente. A Task 1 e `tdd="true"`, entao ela tem o par RED/GREEN:

1. **Task 1 (RED): o episodio e as duas instancias, ainda vermelhos** - `b1b294a` (test)
2. **Task 1 (GREEN): o aviso de nascimento passa a ter marcador duravel** - `d87ca18` (feat)
3. **Task 2: a matriz dos criterios 3, 4, 5 e 6, e o que a decisao PERDE** - `5659880` (test)
4. **Task 3: os portoes AST do anuncio unico, e o silencio que expira** - `6c54747` (test)

## Files Created/Modified

- `l2scanner/agenda.py` - `PREFIXO_ANUNCIO` (em `_PREFIXOS_CONHECIDOS`, com a escolha do balde escrita), `RegistroEmDisco.registrar_anuncio` e o quinto consumidor de `apelido_do_evento`
- `l2scanner/respawn.py` - a nocao de EPISODIO na docstring de modulo, `MARGEM_DO_EPISODIO`, `ancoras_do_boss`, `inicio_do_episodio`, `chave_do_anuncio`, `anunciar_nascimento`
- `l2scanner/sessao.py` - `ResultadoDoTick.nascimentos_calados` e a reordenacao de `_processar_bosses` (ancora, anuncio, despacho)
- `tests/test_anuncio_unico.py` - **novo**: os portoes AST da fase, com shell fabricado por portao e os testes de expiracao real
- `tests/test_respawn.py` - `TestAsAncorasDeUmBoss`, `TestOInicioDoEpisodio`, `TestAChaveDoAnuncio`, `TestAnunciarNascimento`
- `tests/test_sessao.py` - `TestUmNascimentoUmaMensagem` (o tracer) e a matriz: `TestOAlvoCalaDepoisDeOChatFalar`, `TestOFallbackDoAlvoContinuaExistindo`, `TestOSilencioAcabaQuandoONascimentoVoltaASerPossivel`, `TestAAncoragemSobreviveASupressao`, `TestOQueASupressaoPERDE`
- `tests/test_agenda.py` - o gemeo de balde para `PREFIXO_ANUNCIO`

## Decisions Made

Nenhuma decisao nova foi tomada durante a execucao: D-24 a D-30 estavam todas travadas no plano antes da primeira linha de codigo, e o plano foi seguido. Duas observacoes que o plano nao previa e ficam registradas:

- **O rearme em memoria e o marcador se dividem de forma mensuravel.** Na matriz do criterio 3, sete remarcacoes de alvo produzem SEIS deteccoes que chegam ao marcador: a primeira cai dentro do desarme em memoria que a deteccao do chat acabou de fazer no `VigiaDeBosses`. Isso confirma o que o `03-CONTEXT.md` ja dizia — o rearme em memoria e o primeiro filtro barato, e o marcador e a garantia — e a constante `DETECCOES_DE_ALVO` documenta a diferenca no proprio teste.
- **`anunciar_nascimento` nao precisou de um sitio proprio no `--so-agenda`.** A assimetria da Fase 2 (dois sitios de anuncio de janela, um de escrita de ancora) continua valendo aqui em forma ainda mais forte: o anuncio de NASCIMENTO tambem exige pixels, entao ele tem um sitio so. O portao afirma que `__main__.py` nao chama nem `chave_do_nascimento` nem `anunciar_nascimento`.

## Deviations from Plan

None - plan executed exactly as written.

Duas correcoes foram feitas em testes RECEM-ESCRITOS por mim, dentro da mesma tarefa, antes do commit — nao sao desvios do plano nem enfraquecimento de teste existente:

- `tests/test_sessao.py` faltava `import logging` para o teste do rastreio em log.
- Duas expectativas da matriz do criterio 3 diziam 7 deteccoes de alvo onde a mecanica do `VigiaDeBosses` produz 6. A EXPECTATIVA estava errada, e nao a producao; a correcao foi para o numero real, com a razao escrita no proprio arquivo (constante `DETECCOES_DE_ALVO`). Nenhuma afirmacao foi afrouxada: o teste continua exigindo igualdade exata de lista, e nao `>= 1`.

**Total deviations:** 0
**Impact on plan:** nenhum. Nenhum teste das Fases 1 e 2 foi editado para acomodar esta fase.

## Issues Encountered

- **Uma execucao de `pytest` abortou com `KeyboardInterrupt` espurio** no meio de `tests/test_agenda.py`. A reexecucao imediata do mesmo comando passou com 393 testes. Nao reproduziu; e ruido de ambiente, nao defeito.
- **Nenhuma falha de workstream concorrente para atribuir.** O plano avisava para esperar vermelhos em `tests/test_mercado_*.py` e `tests/test_medir_*.py` de `discord` e `mercado`. Na base deste worktree (`46c15a5`) eles estao todos verdes, entao nao ha nada para atribuir por `git log` nem para listar nominalmente.

## Verificacao medida

```
python -m pytest -q
2785 passed, 23 skipped, 2 warnings in 75.86s
```

Os 23 skips sao de ambiente (as ligacoes WinRT do OCR moram no `.venv` e nao no `python` do sistema usado dentro do worktree). O `<verify>` nominal da fase:

```
python -m pytest tests/test_anuncio_unico.py tests/test_respawn.py \
  tests/test_agenda.py tests/test_sessao.py tests/test_bosses.py \
  tests/test_janela_no_relogio.py tests/test_presenca.py -q
```

verde, com o jogo fechado, sem calibracao e sem rede.

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de espera reservada nem componente sem fonte de dado nesta entrega.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. Nao ha endpoint novo, caminho de autenticacao novo nem dependencia nova. O unico caminho novo para o disco e `.agenda/anuncio_*`, ja registrado como T-03-03 e T-03-04 e mitigado pela poda de tres dias e por `ancora_de_chave` ignorar nome torto.

## User Setup Required

None - nenhuma chave de `config.toml` nova, nenhuma dependencia nova, nenhum servico externo.

## Next Phase Readiness

- **O plano 03-02 esta destravado.** Ele e construido em cima da chave duravel decidida aqui, e a forma `anuncio_<YYYY-MM-DD>_<boss-slug>-<HHMM>` esta fixada, testada e escrita a mao no teste (nao gerada pelo proprio produtor).
- **A causa 2 do defeito de campo continua aberta por desenho.** O `VigiaDeBosses` ainda tem rearme por boss e nao por canal, entao a precedencia "o chat sempre avisa, o alvo so como fallback" (D-24) ainda nao esta completa: com o alvo segurando o boss, o anuncio do chat pode ser engolido em memoria antes de chegar ao marcador (T-03-02). E exatamente o escopo do 03-02.
- **Nada nesta entrega toca `ancoras_mais_recentes` nem `_PESO_DA_ORIGEM`**, confirmado por `git diff`. A Fase 2 continua inteira e a ideia adiada (revisitar D-15) continua adiada.

## Self-Check: PASSED

- `tests/test_anuncio_unico.py` existe em disco
- `.planning/workstreams/tiat/phases/03-.../03-01-SUMMARY.md` existe em disco
- Os quatro commits existem: `b1b294a`, `d87ca18`, `5659880`, `6c54747`
- `grep -n "def anuncios" l2scanner/agenda.py` nao encontra nada: o listador irmao nao foi escrito
- `git diff` sobre `l2scanner/respawn.py` nao altera `ancoras_mais_recentes` nem `_PESO_DA_ORIGEM`

---
*Phase: 03-um-aviso-por-nascimento-com-o-chat-mandando-no-alvo*
*Completed: 2026-08-31*
