---
phase: 03-batismo-pelo-whatsapp
workstream: identidade
plan: 01
subsystem: identity
tags: [disk-store, ast-gate, whatsapp-command, content-hash, o-excl, tdd]

requires:
  - "l2scanner/acervo.py — AcervoDeIdentidades, chave_da_assinatura, _nome_de, NOME_VALIDO, CHAVE_VALIDA (Fase 1)"
  - "l2scanner/aprendiz.py — Aprendizado com chave/indice/desfecho (Fase 2)"
  - "l2scanner/sessao.py — _aprender e o funil unico _despachar (Fase 2)"
  - "l2scanner/comandos.py — Comando, COMANDOS_DE_MEMBRO, _AJUDA e o tripwire"
  - "l2scanner/rastreador.py — nomes_reservados e nome_de(indice)"
provides:
  - "l2scanner/batismo.py — o modulo novo, SEM RELOGIO e sem conhecer o mundo"
  - "DIGITOS_DO_APELIDO = 6 e APELIDO_VALIDO, com o numero justificado contra o acervo real"
  - "apelido_da_chave, apelidos_para_escolher (que ESTICA quando seis digitos empatam)"
  - "Resolucao e resolver(prefixo, chaves) — funcao PURA que JAMAIS desempata"
  - "Pendente e pendentes_do_acervo(acervo) — o insumo da varredura de arranque"
  - "montar_pergunta(acervo, pendentes) — o UNICO lugar que marca e o UNICO que redige"
  - "RespostaDoBatismo, interpretar_batismo (a gramatica unica), responder_batismo"
  - "AcervoDeIdentidades.marcar_pergunta (O_CREAT|O_EXCL, OSError -> False)"
  - "AcervoDeIdentidades.nomear (tri-estado, temporario mais os.replace)"
  - "AcervoDeIdentidades.nomeados() e .anonimas(), derivados de _entradas()"
  - "AcervoDeIdentidades(pasta, simulando=False) — o --dry-run que nao queima pergunta"
  - "PREFIXO_PERGUNTA e SUFIXO_TEMPORARIO"
  - "Comando.BATIZAR no enum, no _AJUDA (familia Identidade) e em interpretar_dinamico"
  - "atender_comandos(acervo=, assinaturas_vivas=) e o ramo do despachante"
  - "Sessao.acervo e o gatilho da pergunta no fim de _aprender"
  - "A varredura de arranque em laco_principal, atras do `if despachante is not None`"
  - "batismo.py na tupla MODULOS do portao AST de relogio proprio"
affects:
  - "plano 03-02: BATI-04 (recusa de nome duplicado), BATI-05 (correcao), a fronteira de autorizacao ponta a ponta e o portao AST do ramo novo"
  - "T-03-07: a instancia que nao obedeceu o comando so ve o nome no proximo arranque"

actuals:
  tokens: 42283   # chars/4 sobre o diff realizado (169132 chars em l2scanner/ e tests/)
  tasks: 3
  commits: 5

tech-stack:
  added: []   # zero dependencia nova: re, os, dataclasses e hashlib sao stdlib; numpy ja estava
  patterns:
    - "Marcador de disco como DECISAO, com a assimetria de OSError escolhida por recurso"
    - "Identificador curto DERIVADO do conteudo, nunca guardado, com recusa em vez de desempate"
    - "Gramatica unica, que valida na interpretacao e le no responder"
    - "Uma mensagem para N entradas, em vez de N mensagens"

key-files:
  created:
    - "l2scanner/batismo.py"
    - "tests/test_batismo.py"
  modified:
    - "l2scanner/acervo.py"
    - "l2scanner/comandos.py"
    - "l2scanner/sessao.py"
    - "l2scanner/__main__.py"
    - "tests/test_acervo.py"
    - "tests/test_presenca.py"
    - "tests/test_comandos.py"

key-decisions:
  - "As sete decisoes travadas do CONTEXT implementadas sem reabrir nenhuma; zero checkpoint"
  - "DOIS gatilhos (aprendizado e arranque) com UM marcador: D-04 e por ASSINATURA, e nao por evento"
  - "A varredura de arranque NAO cita posicao, e o desvio e deliberado (ver Registros, item 6)"
  - "O apelido e recortado em 6 digitos, mas a recusa ambigua ESTICA o recorte ate os candidatos ficarem distintos"
  - "responder_batismo devolve um tipo PROPRIO, e nao RespostaDePresenca, para nao arrastar agenda e loot"
  - "interpretar_dinamico usa UM laco de duas palavras para as quatro formas escritas, e nao quatro ramos"
  - "--so-agenda responde ao batismo e NAO varre o acervo"

patterns-established:
  - "Assimetria de OSError escolhida por RECURSO, com a tabela dos dois lados na docstring"
  - "Apelido curto derivado do hash, com recusa por ambiguidade em vez de desempate"
  - "Reorganizacao MONTADA nos testes (blocos de pixel trocados) e AFIRMADA antes do desfecho"
  - "Colisao de prefixo PROCURADA de forma deterministica quando o cenario real nao a produz"

requirements-completed: [BATI-01, BATI-02, BATI-03, OPER-03]

coverage:
  - id: D1
    description: "Ao gravar uma assinatura nova, UMA pergunta sai citando a POSICAO onde ela foi vista, e ela nao se repete no tick seguinte, nem depois de um reinicio, nem na segunda instancia"
    requirement: BATI-01
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOAprendizadoPergunta::test_a_enesima_leitura_grava_UMA_entrada_e_manda_UMA_pergunta"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOAprendizadoPergunta::test_a_pergunta_cita_o_apelido_e_a_linha_em_BASE_1"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaNaoSeRepete::test_mais_vinte_ticks_identicos_nao_perguntam_de_novo"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaNaoSeRepete::test_uma_sessao_NOVA_sobre_a_MESMA_pasta_tambem_nao_pergunta"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestUmaPerguntaPorAssinaturaParaSempre::test_duas_instancias_disputando_produzem_UMA_pergunta"
        status: pass
    human_judgment: false
  - id: D2
    description: "As entradas anonimas que JA ESTAO no disco do usuario tambem sao perguntadas, uma vez so, numa mensagem so, no arranque — o gatilho do aprendizado nunca as alcanca"
    requirement: BATI-01
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco::test_cinquenta_ticks_com_tudo_ja_no_acervo_nao_aprendem_NADA"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOGatilhoDoAprendizadoNaoAlcancaOQueJaEstaNoDisco::test_e_o_disco_continua_intacto_depois_dos_cinquenta_ticks"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAVarreduraDeArranque::test_duas_entradas_anonimas_produzem_UMA_mensagem_com_os_dois_apelidos"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAVarreduraDeArranque::test_rodar_o_arranque_de_novo_nao_produz_mensagem_nenhuma"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAVarreduraDeArranque::test_o_arranque_e_o_tick_dividem_o_MESMO_marcador"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestSemDespachanteONemOArranqueNemOTickMarcam::test_o_arranque_sem_despachante_nao_marca"
        status: pass
    human_judgment: true
    rationale: "A cadeia esta provada com o acervo real COPIADO para tmp_path e com o caminho de producao, e o texto exato esta registrado abaixo. O que so um humano confere e se a mensagem chegando no grupo do WhatsApp e legivel e acionavel na tela do celular — em particular se os tres apelidos hex de seis digitos sao faceis de copiar no meio de um farm."
  - id: D3
    description: "O comando de resposta batiza a assinatura e, a partir da leitura seguinte, os alertas daquela linha saem com o nome dado, sem reiniciar o scanner"
    requirement: BATI-02
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestARespostaBatizaAAssinaturaCerta::test_o_arquivo_de_nome_nasce_com_o_nick_exato"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomePassaAValerSemReiniciar::test_a_lista_viva_ganha_o_nome"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomePassaAValerSemReiniciar::test_o_proximo_extrair_sobre_o_MESMO_frame_ja_diz_o_nome"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomePassaAValerSemReiniciar::test_o_snapshot_de_nomes_reservados_ganha_o_nome"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOTerceiroElo::test_antes_o_nick_e_emprestado_por_posicao_e_depois_nao"
        status: pass
    human_judgment: false
  - id: D4
    description: "A assinatura NAO e tocada pelo batismo (D-06), entao a chave nao muda e o pino continua valendo"
    requirement: BATI-02
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestARespostaBatizaAAssinaturaCerta::test_a_assinatura_NAO_e_tocada_e_por_isso_a_chave_nao_muda"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestAEscritaDoNomeEDefensiva::test_nomear_de_novo_TROCA_o_conteudo_e_nao_duplica"
        status: pass
    human_judgment: false
  - id: D5
    description: "O nome vai para a assinatura PINADA na pergunta, provado pela CHAVE e nao pelo indice da linha: com a party reorganizada entre a pergunta e a resposta, quem esta na linha citada continua sem nome"
    requirement: BATI-03
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOPinoAtravessaAReorganizacaoDaParty::test_a_pergunta_cita_a_linha_e_a_resposta_vai_para_a_CHAVE"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOPinoAtravessaAReorganizacaoDaParty::test_a_linha_citada_continua_SEM_NOME_depois_do_batismo"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOPinoAtravessaOReinicio::test_o_apelido_resolve_igual_numa_instancia_nova"
        status: pass
    human_judgment: false
  - id: D6
    description: "NAO EXISTE sintaxe que alcance uma linha: /batizar 3 Mostarda e recusado como apelido desconhecido, e a recusa DIZ que apelido nao e numero de linha"
    requirement: BATI-03
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestNaoExisteSintaxeQueAlcanceUmaLinha::test_nenhuma_das_tres_formas_escreve_coisa_alguma"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestNaoExisteSintaxeQueAlcanceUmaLinha::test_um_numero_de_linha_cai_em_apelido_DESCONHECIDO"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestNaoExisteSintaxeQueAlcanceUmaLinha::test_o_que_nao_e_hex_cai_em_MALFORMADO"
        status: pass
    human_judgment: false
  - id: D7
    description: "Um prefixo AMBIGUO e RECUSADO com a lista dos candidatos e um desconhecido e recusado dizendo que nao existe. Nunca ha desempate"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestUmPrefixoAmbiguoERecusadoENuncaDesempatado::test_a_recusa_cita_TODOS_os_candidatos_e_a_pasta_fica_inalterada"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestUmPrefixoAmbiguoERecusadoENuncaDesempatado::test_com_um_digito_a_mais_a_MESMA_chamada_resolve"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestResolverJamaisDesempata::test_dois_candidatos_RECUSAM_com_os_dois_na_lista"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestUmPrefixoDesconhecidoERecusadoDizendoOQueExiste::test_a_recusa_lista_os_apelidos_que_estao_sem_nome"
        status: pass
    human_judgment: false
  - id: D8
    description: "A pergunta atravessa o silencio de TvT/Prime (Categoria.SEMPRE), provado no TRANSPORTE com um Despachante de verdade"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOAprendizadoPergunta::test_a_pergunta_sai_com_Categoria_SEMPRE"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaAtravessaOSilencioNoTRANSPORTE::test_a_pergunta_passa_e_um_evento_NORMAL_e_cortado"
        status: pass
    human_judgment: false
  - id: D9
    description: "O marcador NAO e queimado quando nao ha para onde mandar: sem despachante e em --dry-run a pergunta nao consome a unica vez que ela tem (D-05 estendido)"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestSemDespachanteNadaEMarcado::test_sem_despachante_o_marcador_nao_aparece_na_pasta"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestODryRunNaoQueimaOMarcador::test_simulando_marca_sem_encostar_no_disco"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestDepoisDeUmDryRunODiscoMostraAAssimetria::test_a_assinatura_FICA_e_o_marcador_NAO"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestDepoisDeUmDryRunODiscoMostraAAssimetria::test_na_sequencia_dry_run_e_depois_real_a_varredura_e_quem_salva"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestAFraseDoDryRunEVERDADE::test_a_frase_NAO_promete_que_nada_e_gravado_na_identidades"
        status: pass
    human_judgment: false
  - id: D10
    description: "Falha de disco ao marcar NAO manda a pergunta, e a assimetria e o CONTRARIO da agenda (D-05)"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestFalhaDeDiscoNaoManda::test_marcar_devolve_FALSE_quando_o_disco_falha"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestFalhaDeDiscoNaoManda::test_montar_pergunta_devolve_None_quando_o_disco_falha"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestFalhaDeDiscoNaoManda::test_a_agenda_continua_fazendo_o_CONTRARIO"
        status: pass
    human_judgment: false
  - id: D11
    description: "A pergunta nao vira enxurrada: 300 ticks nao fazem a contagem crescer, e duas assinaturas no mesmo tick produzem UM despacho com duas linhas"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaNaoViraEnxurrada::test_trezentos_ticks_produzem_UMA_pergunta"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaNaoViraEnxurrada::test_duas_assinaturas_no_MESMO_tick_produzem_UM_despacho"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAPerguntaNaoViraEnxurrada::test_uma_sessao_que_nao_aprende_nada_produz_ZERO_perguntas"
        status: pass
    human_judgment: false
  - id: D12
    description: "O comando entrou no _AJUDA, o tripwire set(_AJUDA) == set(Comando) segue verde, e BATIZAR NAO esta em COMANDOS_DE_MEMBRO"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestOComandoEDeDono::test_o_tripwire_da_ajuda_segue_verde"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestOComandoEDeDono::test_o_batismo_NAO_e_comando_de_membro"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestFronteiraDeAutorizacao::test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestOCaminhoRealDeLeituraEntregaOComando::test_as_quatro_formas_escritas"
        status: pass
    human_judgment: false
  - id: D13
    description: "A escrita do nome e defensiva na ORIGEM: chave que nao e 64 hex e nome fora do charset devolvem invalido e nao criam arquivo nenhum, nem fora da pasta"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestAEscritaDoNomeEDefensiva::test_uma_chave_que_nao_e_64_hex_e_invalida_e_nao_escreve_nada"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestAEscritaDoNomeEDefensiva::test_um_nome_fora_do_charset_e_invalido_e_nao_escreve_nada"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestAEscritaDoNomeEDefensiva::test_nada_e_escrito_FORA_da_pasta"
        status: pass
    human_judgment: false
  - id: D14
    description: "batismo.py nao tem relogio proprio, esta na tupla MODULOS do portao AST, e nao importa visao, sessao, rastreador, calibracao, loot, agenda nem presenca"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_nenhum_now_de_datetime_na_arvore[batismo.py]"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_a_prova_pega_um_relogio_enfiado_em_CADA_modulo[batismo.py]"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestOBatismoNaoConheceOMundo::test_o_conjunto_de_irmaos_importados"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestQuemConheceOAcervoEOQueOLacoFazComEle::test_so_dois_modulos_conhecem_o_acervo"
        status: pass
    human_judgment: false
  - id: D15
    description: "Os DOIS lacos passam o acervo para atender_comandos, e os DOIS constroem o acervo com simulando"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestOsDoisLacosPassamOAcervo::test_os_dois_passam_acervo"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestOsDoisLacosPassamOAcervo::test_o_que_e_passado_e_a_VARIAVEL_e_nao_um_None"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestOsDoisAcervosNascemComSimulando::test_o_acervo_e_construido_com_simulando"
        status: pass
    human_judgment: false

duration: 41min
completed: 2026-08-31
status: complete
---

# Phase 3 Plan 01: Batismo pelo WhatsApp — Summary

**O scanner passa a PERGUNTAR no WhatsApp quem e a pessoa que ele aprendeu sozinho, e o usuario responde do celular com `/batizar 15caec Mostarda` — e a resposta cola o nome na assinatura que a pergunta PINOU, nunca em "a linha 3 de agora", com o nome valendo na leitura seguinte sem reiniciar nada.**

## Performance

- **Duration:** ~41 min
- **Base:** `f3b8f16`
- **Completed:** 2026-08-31
- **Tasks:** 3
- **Files modified:** 9 (2 criados, 7 modificados)

## Accomplishments

- **`l2scanner/batismo.py`**: modulo novo, SEM RELOGIO e sem conhecer o mundo. Ele nao importa `visao`, `sessao`, `rastreador`, `calibracao`, `loot`, `agenda` nem `presenca` — fala `AcervoDeIdentidades`, `Assinatura` e stdlib. A ausencia de `loot` tem precedente escrito (o `acervo.py` ja se recusou a importar `loot.NICK_VALIDO`, porque `loot` importa `agenda`) e tem razao propria aqui: este modulo e o dono do marcador de D-04, e "uma pergunta para sempre" so continua sendo verdade enquanto nao houver relogio nenhum por perto para virar "uma pergunta por dia".

- **DOIS GATILHOS, UM MARCADOR — e e isso que faz a fase funcionar no unico acervo real que existe.** O gatilho do aprendizado nunca alcanca uma entrada que ja estava no disco: ela entra em `cal.assinaturas` na carga do arranque, casa ~1.000 contra ela mesma, e `Casamento.nome` de uma entrada anonima e a string VAZIA e nao `None` — e `_candidatas_para_aprender` exige `is None`. O caso `test_cinquenta_ticks_com_tudo_ja_no_acervo_nao_aprendem_NADA` afirma isso em 50 ticks, e e a prova de que a varredura de arranque nao e redundancia. Os dois gatilhos passam pelo MESMO `montar_pergunta`, com o MESMO `O_CREAT|O_EXCL`: D-04 e por ASSINATURA, e nao por evento de aprendizado.

- **O pino ja existia e nao precisou ser inventado (D-01).** A chave e o `sha256` do conteudo da mascara, desenhada na Fase 1 exatamente para esta fase: estavel entre reinicios, independente da POSICAO e independente do NOME. A prova do BATI-03 e COMPORTAMENTAL e a reorganizacao e MONTADA, e nao suposta — os blocos de pixel do nome de duas linhas trocam de lugar de verdade no frame real, e o caso AFIRMA, antes do desfecho, que a outra pessoa esta mesmo na linha que a pergunta citou.

- **O terceiro elo, que e a metade do criterio 2 e que quase ninguem escreve.** D-08 lido de forma ingenua e uma linha: trocar a `Assinatura` na lista viva. Ela nao basta. `rastreador.nomes_reservados` e um SNAPSHOT do arranque, e sem `add(nick)` um nick que TAMBEM esteja em `cal.nomes` e que nunca foi calibrado continua sendo entregue por `nome_de(indice)` para qualquer linha nao reconhecida: dois nomes iguais na tela, e um deles mentira. O caso proprio afirma as duas metades — antes do batismo `nome_de` devolve o nick por POSICAO, depois devolve `Membro N`.

- **A assimetria do `OSError` e escolhida por RECURSO, e a tabela dos dois lados esta na docstring.** `agenda.RegistroEmDisco.marcar` colapsa em True porque aviso duplicado vence aviso perdido; `acervo.marcar_pergunta` devolve **False** porque uma pergunta perdida e recuperavel pelo proximo arranque e uma pergunta repetida repete A CADA TICK, para sempre. Ha um caso que afirma os DOIS lados lado a lado, para a assimetria ser visivel e nao so afirmada.

- **O `--dry-run` nao queima a pergunta, e a frase que ele imprime e VERDADE.** `AcervoDeIdentidades(pasta, simulando=True)` afeta SO o `marcar_pergunta`, e nunca o `gravar` — `gravar` e idempotente por conteudo e o `O_EXCL` resolve; um marcador de pergunta e um recurso de uma vez so. A frase do `--dry-run` ganhou uma linha que fala de PERGUNTA e **nao** promete que nada e gravado na `.identidades/`, porque isso seria falso: o `Aprendiz` roda em dry-run e `acervo.gravar` escreve `assinatura_*` na pasta compartilhada. Dois casos guardam a frase: um exige a palavra "pergunta", o outro proibe a promessa mentirosa em tres redacoes.

- **O efeito colateral do dry-run esta AFIRMADO, e nao descoberto depois.** Uma sessao simulada que aprende alguem deixa `assinatura_<chave>.json` e **nao** deixa `perguntado_<chave>`. Na sequencia dry-run-e-depois-real, o scanner real nao pergunta naquele tick e a varredura do arranque seguinte pergunta. Comportamento conhecido e coberto, e nao um bug para alguem "consertar" fazendo `ja_existia` perguntar.

- **O silencio e provado NO TRANSPORTE.** Um `Despachante` de verdade com `em_silencio` verdadeiro corta o evento `Categoria.NORMAL` (`silenciados == 1`) e entrega a pergunta `Categoria.SEMPRE` no outbox. Um despachante falso que so grava tuplas nunca exercitaria o corte, que mora dentro do `despachar` real.

- **O comando nasceu fora do alcance do party-mate sozinho.** `COMANDOS_DE_MEMBRO` e LISTA DE INCLUSAO, entao ninguem precisou lembrar de excluir `BATIZAR`. O tripwire `set(_AJUDA) == set(Comando)` segue verde com a familia "Identidade" nova, e o teste da fronteira derivado de `set(Comando) - COMANDOS_DE_MEMBRO` recusa o comando para o telefone de membro.

## Task Commits

1. **Tarefa 1 (tracer, tdd): a fatia inteira** — `17e1e45` (test, RED) + `2c51f86` (feat, GREEN)
2. **Tarefa 2 (tdd): o pino contra a party reorganizada** — `6d4a670` (test)
3. **Tarefa 3 (tdd): a varredura de arranque e a economia do marcador** — `78a2fa3` (feat)
4. **Conserto achado rodando contra o acervo REAL** — `5f1aa97` (fix)

## Files Created/Modified

- `l2scanner/batismo.py` — **criado** (498 linhas). `DIGITOS_DO_APELIDO`, `APELIDO_VALIDO`, `apelido_da_chave`, `apelidos_para_escolher`, `Resolucao`, `resolver`, `Pendente`, `pendentes_do_acervo`, `montar_pergunta`, `RespostaDoBatismo`, `interpretar_batismo`, `responder_batismo` e as tres recusas redigidas.
- `tests/test_batismo.py` — **criado** (136 casos).
- `l2scanner/acervo.py` — `PREFIXO_PERGUNTA`, `SUFIXO_TEMPORARIO`, o parametro `simulando` no construtor com o incidente de 2026-08-26 19:30 na docstring, e os quatro metodos novos: `marcar_pergunta`, `nomear`, `nomeados`, `anonimas`.
- `l2scanner/comandos.py` — `Comando.BATIZAR` com o registro de por que ele nasce fora de `COMANDOS_DE_MEMBRO`; a linha do `_AJUDA` na familia "Identidade"; os ramos de `interpretar_dinamico` com a auditoria de colisao escrita no fonte; o import da gramatica unica.
- `l2scanner/sessao.py` — `Sessao.acervo` com default `None`; o import de `batismo` (e nao de `acervo`); o bloco da pergunta no fim de `_aprender`, com a trava do despachante e o `Categoria.SEMPRE`; a docstring de `_aprender` deixou de dizer que a fase e calada.
- `l2scanner/__main__.py` — `atender_comandos(acervo=, assinaturas_vivas=)` e o ramo do `BATIZAR` com `avisar_o_grupo` atribuido; a varredura de arranque atras do `if despachante is not None`; `simulando=args.dry_run` nos dois construtores de acervo; a linha nova da frase do `--dry-run`; `acervo=` nos dois lacos e `assinaturas_vivas=` no principal; `acervo=` na `Sessao`.
- `tests/test_acervo.py` — o portao de fronteira de fase ajustado para `{acervo.py, aprendiz.py, batismo.py, __main__.py}`, com a docstring registrando que a Fase 3 chegou.
- `tests/test_presenca.py` — `"batismo.py"` na tupla `MODULOS` e o paragrafo do modulo novo; a linha do `/batizar` na `TABELA` de destinos.
- `tests/test_comandos.py` — `BATIZAR` no conjunto fechado `set(Comando)`; `"Identidade"` em `_FAMILIAS_ESPERADAS`; `<apelido>` nas tres substituicoes derivadas do `_AJUDA`.

## Registros exigidos pelo `<output>` do plano

**1. Contagem de testes:**

| Momento | Passaram | Skipped |
|---------|----------|---------|
| Linha de base (`f3b8f16`) | 3566 | 23 |
| Depois da Tarefa 1 | 3623 | 23 |
| Depois da Tarefa 3 | 3705 | 23 |
| Fim do plano | **3706** | 23 |

Delta: **+140**. Nenhum teste existente foi afrouxado ou removido. Os 23 skipped sao os mesmos da linha de base.

Nota sobre a `<precondition>`: ela previa "3514 passando, 2 skipped ao fim da Fase 2". A linha de base real do worktree e **3566 passando, 23 skipped**, porque a base `f3b8f16` ja traz ondas do workstream `mercado` posteriores a escrita do plano. A suite estava VERDE antes de comecar, que e o que a precondicao de fato exige.

**2. O TEXTO EXATO da pergunta que sai hoje para o acervo REAL do usuario.**

Copiado do caminho de PRODUCAO (`AcervoDeIdentidades` -> `pendentes_do_acervo` -> `montar_pergunta`) rodando sobre os arquivos de verdade de `.identidades/`, copiados para uma pasta temporaria:

```
Aprendi 3 pessoas que ainda estao sem nome:

  0dcf6f
  15caec
  f19e3c

Para dar o nome, responda: /batizar <apelido> <nick>
Exemplo: /batizar 0dcf6f Fulano

So quem calibrou o scanner consegue responder isso.
Se alguma delas nao for gente, e so nao responder: nao pergunto de novo.
```

Uma mensagem so para as tres. Sem posicao nenhuma (ver o item 6). A segunda varredura sobre a mesma pasta devolve `None`. O texto passa por `cp1252` e nao tem travessao.

**SAO TRES ANONIMAS, E NAO DUAS.** O plano e o CONTEXT registraram duas (`15caecfa...`, 161 pixels; `f19e3c92...`, 79 pixels), medidas em 31/08/2026. O disco tem AGORA uma terceira, `0dcf6fc39143e36002527f71e5d4c3cb3cf1d494d041a41949d9536294a1436c`, gravada depois daquela medicao. As duas do plano continuam la, continuam anonimas, e as tres saem na mesma mensagem — que e exatamente o comportamento que "uma mensagem para N entradas" existe para dar. O plano 03-02 e a verificacao devem usar TRES como a contagem de campo.

**3. Despachos produzidos pelo caso de 300 ticks: UM.**

`test_trezentos_ticks_produzem_UMA_pergunta` mede a contagem nos ticks 9, 99 e 299 e afirma `{9: 1, 99: 1, 299: 1}`. A afirmacao e que o numero NAO CRESCE com os ticks, e nao um numero magico de mensagens — molde herdado do caso de 300 recusas da Fase 2.

**4. O conjunto observado pelo portao "quem conhece o acervo":**

```
['__main__.py', 'acervo.py', 'aprendiz.py', 'batismo.py']
```

`sessao.py` e `visao.py` continuam presos do lado de FORA, que sempre foi o ponto do portao: a sessao fala com o `aprendiz` e com o `batismo`, e nunca com o acervo — ela SEGURA um `AcervoDeIdentidades` que o `__main__` construiu, e nunca constroi um.

**5. `interpretar_dinamico` precisou de mais de dois ramos? NAO — precisou de MENOS.**

As quatro formas escritas (`batizar-`, `batizar `, `nomear-`, `nomear `) saem de **UM laco de duas palavras com dois ramos dentro**, e nao de quatro blocos copiados. A razao esta escrita no fonte: `batizar` e `nomear` sao SINONIMOS exatos — nenhuma e abreviacao da outra e nenhuma alcanca nada que a outra nao alcance —, entao dois blocos copiados divergiriam no primeiro ajuste, que e a mesma falha que a gramatica unica em `batismo.interpretar_batismo` existe para evitar. Cada palavra continua tendo as duas formas (hifen e espaco), porque tratar so o hifen foi exatamente o erro que fez `.loot cancelar` DESIGNAR um personagem chamado "cancelar".

**6. O DESVIO DELIBERADO DO CRITERIO 1, para a verificacao nao o ler como criterio nao cumprido.**

O criterio 1 do ROADMAP pede a pergunta "citando a posicao onde ela foi vista".

- A pergunta vinda do **APRENDIZADO** CITA. `Pendente.indice` existe, e o texto diz "vi na linha 4" (base 1). Afirmado por `test_a_pergunta_cita_o_apelido_e_a_linha_em_BASE_1`. **O criterio 1 e cumprido por este gatilho.**
- A pergunta vinda da **VARREDURA DE ARRANQUE** tem `indice=None` e **nao cita posicao**, e esta certo. Aquela entrada foi aprendida numa sessao anterior, possivelmente por outra instancia, e nenhuma posicao de AGORA corresponde a ela. Inventar uma seria a primeira mentira do caminho, no recurso inteiro que existe para nao mentir. Afirmado por `test_a_varredura_NAO_cita_posicao_nenhuma`, que exige a AUSENCIA da palavra.

**O preco esta em quem paga:** as tres entradas reais do usuario, que sao o criterio de aceite mais honesto da fase, serao perguntadas justamente SEM posicao — porque e a varredura que as alcanca. Registrado, e nao escondido.

## Decisions Made

- **As sete decisoes travadas do CONTEXT foram implementadas sem reabrir nenhuma.** Zero checkpoint, zero pergunta.
- **`apelidos_para_escolher` ESTICA o recorte quando seis digitos empatam.** `DIGITOS_DO_APELIDO = 6` e o que a pergunta MOSTRA, mas a recusa ambigua nao pode listar o mesmo apelido duas vezes: a saida que ela oferece ("mande mais digitos") nao teria como ser seguida, e a recusa viraria um beco. O helper cresce ate os recortes ficarem distintos.
- **`Resolucao.candidatos` guarda as CHAVES INTEIRAS, e nao os apelidos recortados.** Quantos digitos separam duas chaves ambiguas e uma decisao de REDACAO, e ela nao pode viver dentro do dado.
- **O apelido e normalizado para minusculo na gramatica.** As chaves sao hex minusculo; quem copiar `15CAEC` de algum lugar continua sendo atendido, e isso nao alarga o charset nem um caractere (o `fullmatch` roda sobre a forma ja minuscula, e `15CAECG` continua recusado).
- **A confirmacao do batismo ECOA no grupo, ao contrario de quase todos os outros ramos.** A PERGUNTA foi publica; uma resposta so no privado deixaria a pergunta pendurada no grupo para sempre, e o proximo party-mate que tentasse responder cairia no `continue` da autorizacao, sem resposta nenhuma. As RECUSAS nao ecoam.
- **`acervo.nomeados()` e chamado no `responder_batismo` mesmo sem o BATI-04.** O plano mandava deixar o ponto de extensao explicito; para nao deixar uma leitura pendurada sem uso, ela alimenta um uso HONESTO — a confirmacao diz se o batismo TROCOU um nome que ja existia. Implementar aqui metade da regra de duplicidade deixaria o plano com uma condicao que se sabe errada; o comentario aponta o 03-02.
- **`--so-agenda` responde ao batismo e NAO varre o acervo.** Aquele e o modo de quem esta com o jogo FECHADO, e uma pergunta "quem e a pessoa da linha 4" chegando com ninguem na frente do jogo convida uma resposta sobre alguem que nao da para ver. O que os dois lacos precisam compartilhar e a RESPOSTA, e ela esta ligada nos dois.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A pergunta dizia "estas" quando havia mais de uma pessoa**

- **Found during:** validacao final, rodando o caminho de producao contra a `.identidades/` REAL do usuario.
- **Issue:** o plural era um sufixo colado — `f"...pessoa{plural} que ainda esta{plural} sem nome"`. Ele acerta o substantivo (`pessoa` -> `pessoas`) e ERRA o verbo: `esta` + `s` da `estas`, que nao e o plural de `esta`. O caminho singular estava correto, entao a suite inteira passava; o erro so apareceria no dia em que houvesse duas assinaturas esperando, que e exatamente o dia do acervo real.
- **Fix:** as duas redacoes escritas por extenso, com o comentario dizendo por que uma regra de plural por concatenacao nao serve para um texto que vai para o WhatsApp.
- **Files modified:** `l2scanner/batismo.py`, `tests/test_batismo.py`
- **Verification:** `test_o_plural_da_frase_esta_certo_nas_DUAS_formas` afirma as duas formas e proibe a string `"estas"` no texto.
- **Committed in:** `5f1aa97`

**2. [Rule 1 - Bug] O helper `retrato_da_pasta` tentava ler diretorios**

- **Found during:** Tarefa 1.
- **Issue:** varios casos apontam o acervo para o proprio `tmp_path`, e a `.agenda/` da `Sessao` nasce ao lado. O retrato tentava `read_bytes()` na pasta irma e levantava `PermissionError`.
- **Fix:** o retrato considera so arquivos, com o comentario dizendo que ler a pasta irma estaria medindo o cenario do teste e nao o acervo.
- **Files modified:** `tests/test_batismo.py`
- **Committed in:** `2c51f86`

**3. [Rule 1 - Bug] O cenario da reorganizacao estava invertido no meu proprio teste**

- **Found during:** Tarefa 2.
- **Issue:** a pergunta citava a linha onde a entrada B morava, e nao a linha onde a entrada A (a PINADA) tinha sido vista. A afirmacao de premissa pegou o erro na hora — que e para isso que ela existe.
- **Fix:** a linha citada passou a ser a de A, e a troca de blocos poe B nela. O caso continua afirmando a premissa antes do desfecho.
- **Files modified:** `tests/test_batismo.py`
- **Committed in:** `6d4a670`

### Provas existentes ESTENDIDAS, nunca afrouxadas

O comando novo alcanca sozinho quatro provas derivadas do enum, e todas exigiram crescimento — que e o comportamento desejado delas, escrito nas proprias docstrings:

- `tests/test_comandos.py::test_o_vocabulario_e_fechado` — `BATIZAR` entrou no conjunto fechado, com o registro de por que.
- `tests/test_comandos.py::test_as_familias_saem_na_ordem_combinada` — `"Identidade"` entrou em `_FAMILIAS_ESPERADAS`, depois de "Loot do Solo Boss".
- `tests/test_comandos.py` — as tres substituicoes derivadas do `_AJUDA` ganharam `<apelido>`. **Sem isso o teste da fronteira de autorizacao passaria VERDE provando nada:** a sintaxe montada seria `/batizar <apelido> J4guar`, que o parser recusa por charset, e o caso afirmaria que o party-mate nao alcanca um comando que NINGUEM alcanca.
- `tests/test_presenca.py::TestDestinoDosComandosAntigos` — a `TABELA` ganhou a linha do `/batizar`, cobrindo o ramo SEM acervo (a recusa, que nao ecoa no grupo). O caminho feliz, que ECOA, e provado em `tests/test_batismo.py` com acervo de verdade.

Os dois portoes de FRONTEIRA DE FASE (`test_so_dois_modulos_conhecem_o_acervo` e a tupla `MODULOS`) foram alterados com a instrucao ja escrita na docstring deles pela Fase 2, redigida para este momento.

### O que NAO foi feito, de proposito

- **A recusa de nome duplicado (BATI-04) e a correcao (BATI-05) nao foram implementadas.** Sao do plano 03-02. O ponto de extensao esta explicito no `responder_batismo`, com o comentario apontando D-07 e o plano.
- **Nenhuma dependencia nova.** `re`, `os`, `dataclasses`, `hashlib` e `pathlib` sao stdlib; `numpy` ja estava. `pyautogui`/`pydirectinput` continuam proibidos por teste.
- **`--so-agenda` nao varre o acervo**, e a razao esta escrita no fonte ao lado da construcao.

## Known Stubs

Nenhum. Todos os simbolos declarados nesta fase tem implementacao e teste. `acervo.nomeados()` e chamado com uso real (a confirmacao de rebatismo) e nao e um stub aguardando o 03-02.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano.

Duas notas sobre o registro, para o 03-02 e para a verificacao:

- **T-03-04 (travessia de caminho) esta mitigado nas DUAS portas de escrita**, e nao so na do nome: `marcar_pergunta` tambem roda `CHAVE_VALIDA.fullmatch` antes de compor o caminho, porque ele tambem escreve um arquivo cujo nome vem de uma chave.
- **T-03-11 (a pergunta absurda) tem a saida escrita no texto**, em uma linha: "Se alguma delas nao for gente, e so nao responder: nao pergunto de novo." O descarte continua sendo IGNORAR, e ignorar so e seguro porque D-04 garante que a pergunta nao volta.

## Self-Check: PASSED

- `l2scanner/batismo.py` — presente
- `tests/test_batismo.py` — presente (136 casos)
- `.planning/workstreams/identidade/phases/03-batismo-pelo-whatsapp/03-01-SUMMARY.md` — presente
- Os cinco commits (`17e1e45`, `2c51f86`, `6d4a670`, `78a2fa3`, `5f1aa97`) existem no historico do worktree, na ordem RED/GREEN de cada tarefa.
- `python -m pytest tests/ -q` -> **3706 passed, 23 skipped**.

## Notes for Next Phase

- **O acervo real tem TRES anonimas, e nao duas.** `0dcf6f`, `15caec` e `f19e3c`. O plano 03-02 e a verificacao humana devem usar tres.
- **A confirmacao ja distingue batismo de rebatismo** ("`15caec` era Kaus e agora e Mostarda"), entao o BATI-05 do 03-02 herda a redacao pronta e precisa acrescentar so o COMANDO de correcao, se ele for separado.
- **`acervo.nomeados()` ja e lido dentro do `responder_batismo`**, no lugar exato onde a comparacao do BATI-04 entra, com a excecao do proprio alvo (D-07) descrita no comentario.
- **T-03-07 continua ACEITO.** A instancia que nao obedeceu o comando so ve o nome no proximo arranque; la a entrada continua ANONIMA, e uma entrada anonima e reconhecida sem virar sujeito de alerta nenhum (APRE-03). O caso de ponta a ponta e do 03-02.
- **O ramo do `BATIZAR` ainda nao tem portao AST proprio para o `avisar_o_grupo`.** A atribuicao esta la e comentada; o irmao do portao e do 03-02, como o plano previu.
