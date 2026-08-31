---
phase: 03-batismo-pelo-whatsapp
workstream: identidade
plan: 02
subsystem: identity
tags: [nome-exclusivo, casefold, correcao, ast-gate, mutacao, divida-medida, tdd]

requires:
  - "03-01: l2scanner/batismo.py (responder_batismo e o ponto de extensao marcado), Comando.BATIZAR, atender_comandos(acervo=, assinaturas_vivas=), a varredura de arranque"
  - "l2scanner/acervo.py — nomear, nomeados, anonimas, marcar_pergunta, simulando (03-01)"
  - "l2scanner/comandos.py — COMANDOS_DE_MEMBRO como LISTA DE INCLUSAO, _AJUDA e o tripwire"
  - "tests/test_aprendiz.py — o molde de _elos_do_arranque/_elos_em_producao e virar_celulas_no_frame"
  - "tests/test_acervo.py — o molde de TestNenhumRastreadorNasceMudo, mortes_apos_zerar e o retrato da pasta"
  - "tests/test_janela_sob_demanda.py — o molde do portao de avisar_o_grupo"
provides:
  - "_dono_do_nome — a comparacao de D-07 por casefold(), com o alvo como excecao"
  - "_recusa_de_nome_ocupado — a recusa redigida, que E a documentacao da saida de T-02-07 e da leitura de T-02-18"
  - "A correcao (BATI-05) pela MESMA operacao, com o nome antigo LIBERADO e a resposta dizendo o que era"
  - "O portao de AST dos CINCO elos novos de __main__.py, com uma mutacao plantada por elo"
  - "O portao de estrutura do avisar_o_grupo no ramo do BATIZAR, com o caso irmao e a guarda contra ramo inexistente"
  - "As tres dividas herdadas (T-02-07, T-02-18, T-03-07) afirmadas em caso, medidas e declaradas aceitas"
affects:
  - "A verificacao da Fase 3: os textos exatos das quatro respostas estao registrados abaixo, rodados contra a .identidades/ REAL"
  - "Qualquer mexida em __main__.py: arrancar qualquer uma das cinco ligacoes desta fase deixa a suite VERMELHA (conferido por mutacao)"
  - "O acervo real do usuario tem hoje SEIS entradas anonimas, e nao tres — ver o Registro 6"

actuals:
  tokens: 19307   # chars/4 sobre o diff realizado (77231 chars, 462701a..3780685)
  tasks: 3
  commits: 5

tech-stack:
  added: []   # zero dependencia nova: ast, dataclasses e re sao stdlib; numpy e cv2 ja estavam
  patterns:
    - "Recusa que carrega a SAIDA, e nao so o nao: a mensagem e a documentacao da unica saida que existe"
    - "Regra mais estrita justificada como SUBCONJUNTO da frouxa, e nao como segunda definicao de igualdade"
    - "Resposta DERIVADA DO ESTADO em vez de um segundo caminho de codigo (D-06)"
    - "Portao de AST por ELO com mutacao plantada, conferido plantando a mutacao no fonte de producao REAL"
    - "Divida herdada afirmada em caso, com o numero MEDIDO nesta maquina e o veto contra o conserto errado"

key-files:
  created: []
  modified:
    - "l2scanner/batismo.py"
    - "tests/test_batismo.py"
    - "tests/test_comandos.py"

key-decisions:
  - "A comparacao de BATI-04 e por casefold() contra acervo.nomeados(), com a excecao do PROPRIO alvo (D-07)"
  - "A recusa cita o nome como esta GRAVADO, e nao como foi digitado — achado rodando contra o acervo real"
  - "A frase 'o nome antigo ficou livre' so sai quando ele ficou mesmo livre: corrigir kaus para Kaus e a mesma entrada"
  - "nomes_reservados NAO perde o nome antigo numa correcao, e ha caso que afirma isso com a razao na mensagem"
  - "O portao dos cinco elos e IRMAO e nao fundido com o da Fase 2: dois portoes, duas fases, dois relatorios"
  - "A substituicao de <apelido> em tests/test_comandos.py ja tinha entrado no 03-01; aqui so a docstring cresceu"

patterns-established:
  - "Mensagem de recusa auditada contra o ESTADO do disco, e nao contra o que o usuario digitou"
  - "Mutacao plantada no fonte de PRODUCAO (e restaurada) como verificacao de que o portao recebe de verdade"
  - "Fronteira de drift REMEDIDA na fixture da fase, em vez de repetir o numero da fase anterior"

requirements-completed: [BATI-04, BATI-05]

coverage:
  - id: D16
    description: "Batizar uma SEGUNDA assinatura com um nome que ja pertence a outra e RECUSADO, a resposta diz QUAL entrada tem o nome, e o acervo fica inalterado byte a byte"
    requirement: BATI-04
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_batizar_B_com_o_nome_de_A_e_RECUSADO_e_nada_e_escrito"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_a_recusa_NAO_ecoa_no_grupo"
        status: pass
    human_judgment: false
  - id: D17
    description: "A recusa e ACIONAVEL: cita o apelido da entrada dona, a forma do comando que libera o nome, e as duas frases das dividas herdadas"
    requirement: BATI-04
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_a_recusa_diz_QUAL_entrada_tem_o_nome_e_COMO_liberar"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_a_recusa_carrega_a_leitura_de_T0218"
        status: pass
    human_judgment: true
    rationale: "O texto esta registrado abaixo palavra por palavra, rodado pelo caminho de producao contra a .identidades/ REAL. O que so um humano confere e se, lendo no celular no meio de um farm, a saida (batizar a outra com outro nome) fica obvia — ela e a UNICA saida que existe, e a mensagem e o unico lugar onde alguem vai procurar por ela."
  - id: D18
    description: "A comparacao ignora a caixa, e a recusa cita o nome como esta GRAVADO"
    requirement: BATI-04
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_a_comparacao_IGNORA_a_caixa"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_a_recusa_cita_o_nome_COMO_ESTA_GRAVADO_e_nao_como_foi_digitado"
        status: pass
    human_judgment: false
  - id: D19
    description: "A excecao da recusa e o PROPRIO alvo: rebatizar a entrada X de kaus para Kaus e ACEITO e grava"
    requirement: BATI-04
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestONomeQueJaEDeOutraPessoa::test_rebatizar_a_PROPRIA_entrada_em_outra_caixa_e_ACEITO"
        status: pass
    human_judgment: false
  - id: D20
    description: "Um batismo errado e corrigido pelo MESMO comando, sem calibrar.bat: o numero de entradas nao muda e a assinatura fica byte a byte identica"
    requirement: BATI-05
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOBatismoErradoSeConsertaPelaMesmaPorta::test_corrigir_grava_o_nome_novo_e_a_assinatura_fica_INTACTA"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestOBatismoErradoSeConsertaPelaMesmaPorta::test_a_resposta_da_correcao_cita_o_nome_ANTIGO_e_o_NOVO"
        status: pass
    human_judgment: false
  - id: D21
    description: "O nome antigo e LIBERADO de volta e serve imediatamente para outra entrada: o acervo termina com uma entrada por pessoa"
    requirement: BATI-05
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestOBatismoErradoSeConsertaPelaMesmaPorta::test_o_nome_antigo_e_LIBERADO_e_serve_para_a_outra_entrada"
        status: pass
    human_judgment: false
  - id: D22
    description: "A correcao vale no MESMO tick nas duas direcoes: o nome novo entra na lista viva NO LUGAR e o antigo sai; nomes_reservados ganha o novo e NAO perde o antigo"
    requirement: BATI-05
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestACorrecaoValeNoMesmoTickNasDuasDirecoes::test_a_lista_viva_troca_NO_LUGAR_e_o_nome_antigo_some"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestACorrecaoValeNoMesmoTickNasDuasDirecoes::test_nomes_reservados_ganha_o_NOVO_e_NAO_perde_o_antigo"
        status: pass
    human_judgment: false
  - id: D23
    description: "Uma gravacao que falha nao mente: a resposta nao promete nada e os dois containers vivos ficam intactos"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestAGravacaoQueFalhaNaoMente::test_com_falhou_a_resposta_nao_promete_e_os_vivos_ficam_intactos"
        status: pass
    human_judgment: false
  - id: D24
    description: "Criterio 6: com o telefone de DONO o batismo grava; com o de um [[membro]] nada e obedecido, nada e escrito e nenhum despacho sai"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestQuemPodeBatizar::test_o_DONO_batiza_e_o_nome_e_gravado"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestQuemPodeBatizar::test_o_MEMBRO_nao_obedece_nao_escreve_e_nao_despacha"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestQuemPodeBatizar::test_o_BATIZAR_esta_na_lista_de_recusa_DERIVADA"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestQuemPodeBatizar::test_o_dono_alcanca_SEM_estar_declarado_membro"
        status: pass
    human_judgment: false
  - id: D25
    description: "A ajuda nao ensina sintaxe quebrada: a sintaxe e os apelidos anunciados batizam de verdade, e o tripwire set(_AJUDA) == set(Comando) segue verde"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestAAjudaEnsinaUmaSintaxeQueFUNCIONA::test_a_sintaxe_anunciada_batiza_de_verdade"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAAjudaEnsinaUmaSintaxeQueFUNCIONA::test_os_apelidos_anunciados_tambem_batizam"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#test_toda_sintaxe_anunciada_volta_como_o_comando_certo"
        status: pass
    human_judgment: false
  - id: D26
    description: "T-02-07 afirmado em cinco passos, com o dano residual declarado aceito"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestADividaT0207AFirmadaEAceita::test_a_historia_inteira_em_cinco_passos"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestADividaT0207AFirmadaEAceita::test_o_dano_RESIDUAL_e_afirmado_e_declarado_aceito"
        status: pass
    human_judgment: false
  - id: D27
    description: "T-02-18 afirmado com a fronteira MEDIDA nesta fixture, uma pergunta com duas linhas, e a recusa que diz que a segunda sem nome nao faz mal"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestADividaT0218AFirmadaEAceita::test_a_fronteira_MEDIDA_e_a_razao_de_a_segunda_entrada_nascer"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestADividaT0218AFirmadaEAceita::test_as_duas_entradas_saem_como_DUAS_LINHAS_da_MESMA_pergunta"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestADividaT0218AFirmadaEAceita::test_a_segunda_e_recusada_e_a_recusa_diz_que_isso_nao_faz_mal"
        status: pass
    human_judgment: false
  - id: D28
    description: "T-03-07: a instancia que nao obedeceu continua ANONIMA e CALA — nome vazio, rotulo Membro N e ZERO eventos — e o disco ja tem o nome para o proximo arranque"
    verification:
      - kind: integration
        ref: "tests/test_batismo.py#TestAInstanciaQueNaoObedeceuContinuaAnonimaECALA::test_a_segunda_lista_viva_continua_anonima_e_produz_ZERO_eventos"
        status: pass
      - kind: integration
        ref: "tests/test_batismo.py#TestAInstanciaQueNaoObedeceuContinuaAnonimaECALA::test_e_o_DISCO_ja_tem_o_nome_para_o_proximo_arranque"
        status: pass
    human_judgment: false
  - id: D29
    description: "Arrancar qualquer uma das cinco ligacoes novas do __main__.py deixa a suite VERMELHA"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestNenhumaLigacaoDoBatismoSomeEmSilencio::test_as_cinco_ligacoes_estao_no_fonte_de_producao"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestNenhumaLigacaoDoBatismoSomeEmSilencio::test_o_portao_nao_passa_por_vacuidade"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestNenhumaLigacaoDoBatismoSomeEmSilencio::test_o_detector_nao_acusa_o_fonte_que_cumpre"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestNenhumaLigacaoDoBatismoSomeEmSilencio::test_o_detector_acusa_SO_UM_dos_lacos_passando_o_acervo"
        status: pass
    human_judgment: false
  - id: D30
    description: "O ramo do BATIZAR atribui avisar_o_grupo, e o detector acusaria um ramo fabricado sem a atribuicao"
    verification:
      - kind: unit
        ref: "tests/test_batismo.py#TestORamoDoBatismoAtribuiAvisarOGrupo::test_o_ramo_de_producao_atribui_a_flag"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestORamoDoBatismoAtribuiAvisarOGrupo::test_o_detector_acusaria_um_ramo_fabricado_SEM_a_atribuicao"
        status: pass
      - kind: unit
        ref: "tests/test_batismo.py#TestORamoDoBatismoAtribuiAvisarOGrupo::test_o_detector_falha_alto_quando_o_ramo_nao_existe"
        status: pass
    human_judgment: false

duration: 52min
completed: 2026-08-31
status: complete
---

# Phase 3 Plan 02: Batismo pelo WhatsApp — O Nome Exclusivo e o Erro Reversivel — Summary

**Dar duas vezes o mesmo nome deixou de ser possivel, e errar o nome deixou de ser permanente: o mesmo comando que batiza tambem conserta, e a recusa diz, com o apelido na mao, qual entrada ja tem aquele nome e como liberar — que e a unica saida que existe num acervo sem comando de esquecer.**

## Performance

- **Duration:** ~52 min
- **Base:** `462701a`
- **Completed:** 2026-08-31
- **Tasks:** 3
- **Files modified:** 3 (0 criados, 3 modificados)

## Accomplishments

- **A recusa de BATI-04 nao e um "nao": ela e a documentacao da unica saida que este projeto tem.** Um recorte contaminado pode ter virado entrada, e o usuario pode ter respondido a pergunta dela — o nome fica QUEIMADO. Nao ha comando de esquecer no v1, entao a saida e batizar a entrada de lixo com outro nome, e a recusa e o unico lugar do produto onde alguem vai procurar por essa instrucao. Ela cita o apelido da entrada dona (a unica coisa acionavel), a forma do comando e um exemplo montado com aquele apelido.

- **A comparacao por `casefold()` esta justificada contra a proibicao que `carregar_identidades` escreveu, e a justificativa e a DIRECAO do erro.** La a igualdade e exata porque um erro para o lado frouxo custa silencio; aqui um erro frouxo custa duas entradas chamadas `Mostarda` e `mostarda`, e dois alertas que um humano le como a mesma pessoa. A regra estrita e um SUBCONJUNTO da frouxa: ela so recusa mais, e recusar mais nao pode produzir um nome errado. Nao ha comparacao de imagem, limiar novo nem "parecido o suficiente" — a chave de conteudo continua sendo a unica definicao de mesma pessoa (D-01).

- **A correcao e a MESMA operacao, e a diferenca esta so na RESPOSTA (D-06).** Nao nasceu comando novo, nao nasceu simbolo publico novo e nao nasceu segundo caminho. O que muda e a redacao derivada do estado: quando ja havia um nome, a resposta diz qual era e diz que ele ficou livre. Um `/corrigir-<apelido> <nick>` teria a mesma implementacao com outro nome, e os dois divergiriam no primeiro ajuste — a forma de defeito que este projeto ja nomeou tres vezes.

- **A frase "ficou livre" so sai quando ele ficou mesmo livre.** Corrigir `kaus` para `Kaus` e a excecao de D-07 sobre a MESMA entrada: o nome continua ocupado por ela, so que com outra caixa. Dizer que ficou livre mandaria o usuario tentar um batismo que sera recusado.

- **`nomes_reservados` NAO perde o nome antigo, e isso e deliberado, com caso proprio.** O conjunto e um conservador: ele so diz "este nome nao serve de rotulo por POSICAO", e nunca "esta pessoa esta aqui". Tirar o antigo o faria voltar a ser emprestado por posicao para qualquer linha nao reconhecida — e um nome que ja pertenceu a uma assinatura nunca deveria voltar a ser um palpite posicional.

- **As tres dividas herdadas viraram CASO, com numero, e nao paragrafo de relatorio.** T-02-07 e uma historia de cinco passos com afirmacao entre cada dois; T-02-18 tem a fronteira REMEDIDA nesta fixture (e nao o numero da Fase 2 repetido); T-03-07 e afirmado por COMPORTAMENTO — zero eventos e rotulo `Membro N` —, e nao por leitura de campo. As tres docstrings vetam o conserto errado por escrito.

- **O portao dos cinco elos foi conferido plantando as mutacoes no `__main__.py` REAL, e nao so no fonte fabricado.** As seis (cinco elos mais o `avisar_o_grupo`) deixam a suite VERMELHA. A Fase 1 descobriu em campo que uma garantia provada estava desligada; a Fase 2 descobriu a mesma forma por mutacao; a Fase 3 nao vai descobrir uma terceira vez.

## Task Commits

1. **Tarefa 1 (tdd): o nome que ja e de outra, e o batismo errado** — `10940a3` (test, RED) + `e458f39` (feat, GREEN)
2. **Tarefa 2: a fronteira nos dois telefones e as tres dividas afirmadas** — `8661514` (test)
3. **Tarefa 3: as cinco ligacoes que poderiam sumir em silencio** — `bd1e126` (test)
4. **Conserto achado rodando contra o acervo REAL** — `3780685` (fix)

## Registros exigidos pelo `<output>` do plano

**1. Contagem de testes.**

| Momento | Passaram | Skipped |
|---------|----------|---------|
| Linha de base (`462701a`) | 3706 | 23 |
| Depois da Tarefa 1 (GREEN) | 3718 | 23 |
| Depois da Tarefa 2 | 3731 | 23 |
| Depois da Tarefa 3 | 3743 | 23 |
| Fim do plano | **3744** | 23 |

Delta: **+38**. Nenhum teste existente foi afrouxado ou removido. Os 23 skipped sao os mesmos da linha de base. `tests/test_batismo.py` passou de 136 para **174 casos**.

Nota sobre a `<precondition>` da Tarefa 1: ela exigia a suite verde com a contagem registrada no `03-01-SUMMARY.md`, e foi cumprida exatamente — 3706 passed, 23 skipped, o mesmo numero daquele relatorio.

**2. O TEXTO EXATO da recusa de nome duplicado**, copiado do caminho de PRODUCAO (`AcervoDeIdentidades` -> `responder_batismo`) rodando sobre a `.identidades/` REAL do usuario, copiada para uma pasta temporaria. Apelidos de verdade.

```
Nao batizei ninguem: o nome Mostarda ja e da assinatura 0dcf6f. Nada mudou, nem numa entrada nem na outra.
Se as duas forem a mesma pessoa, eu aprendi o rosto dela duas vezes. Nesse caso a segunda pode ficar sem nome sem problema nenhum: assinatura sem nome continua sendo reconhecida e nunca vira sujeito de alerta.
Para o nome Mostarda ficar livre aqui, batize a 0dcf6f com outro nome. Essa e a unica saida: nao existe comando de esquecer uma assinatura.
Exemplo: /batizar 0dcf6f Fulano
```

`grupo` e `None`: recusa nao ecoa. O texto passa por `cp1252` e nao tem travessao.

Quando as grafias diferem so na caixa (`/batizar 15caec mostarda`), entra UMA linha a mais, na segunda posicao:

```
Para mim mostarda e Mostarda sao o mesmo nome, a caixa nao conta: dois alertas que so diferem na caixa ninguem consegue distinguir.
```

E o **TEXTO EXATO da correcao** (`/batizar 0dcf6f Titander`, com a entrada ja chamada `Mostarda`):

```
Pronto: 0dcf6f era Mostarda e agora e Titander. O nome Mostarda ficou livre. Os alertas dessa pessoa passam a sair com esse nome, sem reiniciar nada.
```

`grupo`: `0dcf6f agora e Titander.`

O batismo NOVO, para contraste (`/batizar 15caec Mostarda` depois de `Mostarda` ter sido liberado):

```
Pronto: 15caec agora e Mostarda. Os alertas dessa pessoa passam a sair com esse nome, sem reiniciar nada.
```

**3. Quantas celulas foram viradas para montar o par de T-02-18, e a correlacao MEDIDA NESTA MAQUINA.**

A fronteira foi REMEDIDA na fixture desta fase, e nao copiada da Fase 2 — repetir o numero de la o transformaria, na primeira leitura de outra pessoa, de numero medido em constante inventada.

| | Fase 2 (nick `TioMad`) | Esta fixture (linha 1) |
|---|---|---|
| celulas da mascara | 2000 | 2000 |
| pixels de texto | 60 | 48 |
| ultima ACIMA do limiar | 42 -> 0.7531 | **34 -> 0.7515** |
| primeira ABAIXO | 43 -> 0.7492 | **35 -> 0.7467** |
| fracao da mascara | 2,15% | **1,75%** |
| fracao do SINAL DE TEXTO | 71,7% | **72,9%** |

A leitura generaliza e piora: **o que separa a dedupe que vale da que nao vale sao ~72% do sinal de texto, e nao ~2% da mascara.** Num nick curto a fronteira chega ainda mais cedo, e o modelo de drift usado ACENDE celulas, entao os dois numeros sao limites OTIMISTAS. O par de T-02-18 desta fase e montado com **35 celulas**, e a correlacao e afirmada nas DUAS margens antes de qualquer desfecho.

**4. Quais das cinco mutacoes plantadas exigiram ajuste no detector, e por que.**

| Mutacao | Ajuste no detector | Por que |
|---|---|---|
| M1 `Sessao(acervo=...)` arrancado | nenhum | mesma forma do `aprendiz=` da Fase 2 |
| M2 so um dos lacos passa o `acervo` | nenhum | a exigencia e POR CHAMADA, entao o laco que ainda cumpre continua sendo achado e o outro e acusado |
| M3 `assinaturas_vivas=` arrancado | **sim** | este elo nao pode ser exigido por chamada: o laco da agenda passa `None` COM RAZAO, porque la nao existe tela. Virou um elo de PRESENCA — a queixa nasce quando ha chamadas de `atender_comandos` e NENHUMA passa a lista viva |
| M4 varredura de arranque arrancada | **sim, duas vezes** | (a) `montar_pergunta` tambem e chamada em `sessao.py` (o gatilho do aprendizado), entao contar qualquer ocorrencia deixaria a mutacao passar; o elo foi ancorado no `FunctionDef` chamado `laco_principal`. (b) A mutacao no fonte fabricado tinha de remover o BLOCO `if despachante is not None:` inteiro e nao so a linha de dentro — arrancar so a linha deixa um `if` sem corpo, que nem compila |
| M5 `simulando=` arrancado | **sim, de forma** | segue o molde do `Rastreador` e nao o dos elos: a pergunta nao e "esta ligacao existe" e sim "toda chamada DECIDE sobre um argumento cujo default e silencioso". A resposta certa pode ser `False`, entao o portao exige a DECISAO e nunca um valor |

**E as seis foram plantadas no `__main__.py` REAL, uma a uma, com o arquivo restaurado em seguida.** As seis deixam a suite VERMELHA:

| Mutacao no fonte de producao | Desfecho |
|---|---|
| M1 `Sessao(...)` sem `acervo=` | 2 failed |
| M2 `laco_da_agenda` sem `acervo=` | 1 failed |
| M3 `laco_principal` sem `assinaturas_vivas=` | 2 failed |
| M4 `montar_pergunta(...)` -> `pergunta = None` | 2 failed |
| M5 `AcervoDeIdentidades(...)` sem `simulando=` | 1 failed |
| M6 ramo do `BATIZAR` sem `avisar_o_grupo = False` | 1 failed |

**5. O estado de `W-01`, `W-02` e `W-03` do `02-VERIFICATION.md` no fim da fase.**

| Item | Estado | Onde |
|---|---|---|
| W-01 (tres linhas de producao sem guarda) | **FECHADO antes desta fase comecar** | `tests/test_aprendiz.py::TestNenhumaLigacaoDoAprendizSomeEmSilencio` guarda `ELO_SESSAO`, `ELO_LISTA_VIVA` e `ELO_AJUSTES` com portao de AST, guarda contra vacuidade e uma mutacao plantada por elo. **Nao foi reimplementado aqui**, como o plano manda |
| W-02 (`LEITURAS_PARA_APRENDER = 5` solto) | **FECHADO antes desta fase comecar** | `tests/test_aprendiz.py::TestOCincoLeiturasEstaPreso`, que prende a DERIVACAO (a familia CARA do `rastreador.Ajustes`) e nao so o literal |
| W-03 (bookkeeping desatualizado) | **FECHADO** | `ROADMAP.md` marca `- [x] 02-02-PLAN.md`; `REQUIREMENTS.md` marca `- [x] APRE-04` e a tabela diz `Complete` |

O `02-VERIFICATION.md` continua desatualizado em relacao ao codigo — os tres itens ja estavam pagos quando esta onda comecou. Registrado aqui para a verificacao da Fase 3 nao os ler como pendentes.

**6. O ACERVO REAL CRESCEU DE NOVO, E O NUMERO DE CAMPO E OUTRO.**

| Momento | Anonimas no disco |
|---|---|
| `03-CONTEXT.md` (31/08, manha) | 2 (`15caec`, `f19e3c`) |
| `03-01-SUMMARY.md` | 3 (mais `0dcf6f`) |
| **Medido nesta onda, no caminho de producao** | **6** (mais `70f0f1`, `94822d`, `bf53b2`) |

Nenhuma das seis casa a chave de nenhuma das quatro calibradas (`Mostarda c418e1`, `Titander 772128`, `Pirulito ea1c60`, `Welazkez c15333`), entao `carregar_identidades` nao descarta nenhuma: `Identidades: 10 assinatura(s) conhecida(s), 6 sem nome`. A pergunta de arranque que sai hoje lista as SEIS numa mensagem so.

Isto nao muda nada do que esta implementado — "uma mensagem para N entradas" existe exatamente para isso —, mas muda o roteiro da verificacao humana: sao seis apelidos a batizar, e nao tres.

## Files Created/Modified

- `l2scanner/batismo.py` — `_dono_do_nome` (a comparacao de D-07 com a justificativa do `casefold()` contra `carregar_identidades`), `_recusa_de_nome_ocupado` (a recusa redigida, com o comentario dizendo que as duas frases do meio sao a mitigacao escrita de T-03-11 e T-03-12), a leitura UNICA de `nomeados()` alimentando as duas perguntas, a redacao da correcao com o nome antigo e o "ficou livre" condicional, e o comentario do `nomes_reservados` sobre por que o antigo nao sai.
- `tests/test_batismo.py` — 38 casos novos (136 -> 174), em 10 classes: BATI-04, BATI-05, a correcao no mesmo tick, a gravacao que falha, a fronteira de autorizacao, a ajuda, T-02-07, T-02-18, T-03-07, o portao dos cinco elos e o portao do `avisar_o_grupo`. Mais os helpers `duas_entradas`, `recorte_contaminado`, `virar_celulas_no_frame`, `correlacao_contra`, `com_hp` e `mortes_apos_zerar` (os tres ultimos COPIADOS e nao importados, pela razao que o topo do arquivo ja escreve).
- `tests/test_comandos.py` — **so a docstring** de `test_toda_sintaxe_anunciada_volta_como_o_comando_certo`, dizendo que sao TRES marcadores, que o terceiro nasceu com o batismo, e por que acrescentar uma substituicao ESTENDE em vez de afrouxar.

## Decisions Made

- **A recusa cita o nome como esta GRAVADO.** Ver Deviations, item 1.
- **A frase "ficou livre" e condicional**, e a condicao e `nome_anterior.casefold() != nick.casefold()`. Corrigir a caixa da propria entrada nao libera nada.
- **`acervo.nomeados()` e lido UMA vez** e alimenta a recusa e a confirmacao. Uma segunda leitura entre as duas abriria uma janela em que a outra instancia do usuario mudou o disco no meio, e a resposta descreveria um estado que nunca existiu.
- **O elo da lista viva e de PRESENCA, e nao por chamada.** O laco da agenda passa `None` com razao. Ver Registro 4, M3.
- **O elo da varredura e ancorado no `laco_principal`**, e nao em qualquer `montar_pergunta` do pacote. Ver Registro 4, M4.
- **O portao novo e IRMAO do da Fase 2, e nao uma fusao.** Os dois guardam fases diferentes; fundi-los faria uma queixa de um aparecer no relatorio do outro.
- **A substituicao de `<apelido>` em `tests/test_comandos.py` nao precisou ser feita:** ela ja tinha entrado no 03-01, nas tres provas derivadas do `_AJUDA`. Ver Deviations, item 2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A recusa citava o nome como foi DIGITADO, e nao como esta gravado**

- **Found during:** validacao final, rodando o caminho de producao contra a `.identidades/` REAL do usuario.
- **Issue:** `/batizar 15caec mostarda` respondia *"o nome mostarda ja e da assinatura 0dcf6f"*. O disco nao tem `mostarda` em lugar nenhum — aquela entrada se chama `Mostarda`. A frase era falsa sobre o estado e mandava o usuario procurar por uma grafia que nao existe, no recurso inteiro que existe para nao mentir. A suite ficava verde porque todo caso da caixa afirmava a recusa e o apelido, e nenhum afirmava QUAL nome a recusa cita.
- **Fix:** a recusa passa a citar sempre o nome gravado, e quando as duas grafias diferem ela diz por que sao o mesmo nome (sem essa linha o usuario le duas strings diferentes e conclui que o scanner esta quebrado).
- **Files modified:** `l2scanner/batismo.py`, `tests/test_batismo.py`
- **Verification:** `test_a_recusa_cita_o_nome_COMO_ESTA_GRAVADO_e_nao_como_foi_digitado`
- **Committed in:** `3780685`

**2. [Rule 3 - Bloqueio inexistente] O item 1 da Tarefa 2 ja estava feito**

- **Found during:** Tarefa 2.
- **Issue:** o plano manda acrescentar `.replace("<apelido>", ...)` em `tests/test_comandos.py`, avisando que sem isso o caso quebraria. Ele **nao quebrava**: o 03-01 ja tinha acrescentado a substituicao nas TRES provas derivadas do `_AJUDA`, com `_APELIDO_DE_EXEMPLO = "0123ab"` e o comentario explicando o charset. O `03-01-SUMMARY.md` registra isso em "Provas existentes ESTENDIDAS".
- **Fix:** nada a acrescentar no codigo. A docstring do tripwire cresceu com o argumento que o plano pedia (por que estender nao e afrouxar, e por que cada marcador tem charset proprio), porque essa era a parte que ainda faltava: a substituicao estava escrita, a razao nao.
- **Files modified:** `tests/test_comandos.py`
- **Committed in:** `8661514`

**3. [Rule 3 - Ajuste do detector] A mutacao da varredura nao compilava**

- **Found during:** Tarefa 3.
- **Issue:** arrancar so a linha `pergunta = montar_pergunta(...)` do `FONTE_QUE_CUMPRE` deixava o `if despachante is not None:` sem corpo, e `ast.parse` levantava `IndentationError` — o caso falhava por sintaxe e nao por deteccao.
- **Fix:** a mutacao remove o BLOCO inteiro, que e tambem a mutacao realista num diff de verdade. O comentario ao lado registra a razao.
- **Files modified:** `tests/test_batismo.py`
- **Committed in:** `bd1e126`

### Fora do escopo, registrado e nao consertado

- **Um nome que colide com uma CALIBRADA nao e recusado.** `_dono_do_nome` compara contra `acervo.nomeados()`, que e exatamente o que D-07 manda ("compara contra os `nome_<chave>` gravados"). Batizar uma entrada do acervo com `Mostarda`, que ja e o nome de uma assinatura CALIBRADA, e aceito — e `carregar_identidades` entao descarta aquela entrada do acervo no proximo arranque, pela regra (b) da precedencia (Fase 1). O desfecho e seguro (a calibrada continua reconhecendo a pessoa) e a regra que o produz e antiga e deliberada, mas ele nao esta coberto por caso nesta fase e nao foi decidido por ninguem para esta fase. **Registrado para a verificacao decidir**; alargar a comparacao para incluir `cal.nomes` seria mudar D-07 sem o usuario na mesa.

## Issues Encountered

- `python -m pytest tests/ -q` foi interrompido duas vezes por um `KeyboardInterrupt` vindo do ambiente, sempre em `tests/test_agenda.py:1141`, sem relacao com esta fase. As execucoes seguintes completaram normalmente e nenhum caso falhou.

## Known Stubs

Nenhum. Todo simbolo novo tem implementacao e caso. Nenhuma entrada foi deixada com dado vazio fluindo para a tela.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. Zero dependencia nova (`T-03-SC` continua valendo: nao houve tarefa de instalacao). Duas notas de registro:

- **T-03-13 e T-03-14 mitigados com prova byte a byte:** o retrato da pasta e afirmado identico antes e depois de CADA recusa desta fase, e nao so a resposta.
- **A superficie nova de escrita continua sendo a mesma porta:** `acervo.nomear`, com `CHAVE_VALIDA` e `NOME_VALIDO` no escritor. Esta fase nao acrescentou nenhum caminho de escrita.

## User Setup Required

Nenhum. Zero dependencia nova, zero variavel de ambiente nova, zero passo de instalacao. O comando ja existia desde o 03-01.

## Next Phase Readiness

- **Os criterios 4, 5, 6 e 7 do ROADMAP sao demonstraveis por comando, com o jogo fechado e sem rede** — e os textos exatos das quatro respostas estao registrados acima, rodados contra o acervo real.
- **A verificacao humana deve usar SEIS apelidos, e nao tres.** Ver Registro 6.
- **A colisao com nome CALIBRADO (fora do escopo, acima) e a unica pergunta aberta que esta onda deixa**, e ela e uma pergunta para o usuario, e nao um defeito.

## Self-Check: PASSED

- `l2scanner/batismo.py` — presente, com `_dono_do_nome` e `_recusa_de_nome_ocupado`
- `tests/test_batismo.py` — presente, 174 casos coletados
- `.planning/workstreams/identidade/phases/03-batismo-pelo-whatsapp/03-02-SUMMARY.md` — presente
- Os cinco commits (`10940a3`, `e458f39`, `8661514`, `bd1e126`, `3780685`) existem no historico do worktree, na ordem RED/GREEN da Tarefa 1
- `python -m pytest tests/ -q` -> **3744 passed, 23 skipped**
