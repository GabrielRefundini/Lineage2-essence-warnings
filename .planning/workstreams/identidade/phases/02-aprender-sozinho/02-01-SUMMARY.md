---
phase: 02-aprender-sozinho
workstream: identidade
plan: 01
subsystem: identity
tags: [hamming, ast-gate, disk-store, opencv, party-window, config-toml, tdd]

requires:
  - "l2scanner/acervo.py — AcervoDeIdentidades.gravar tri-estado (Fase 1)"
  - "l2scanner/identidade.py — Assinatura, mascara_de_texto, LIMIAR_DE_CASAMENTO, PIXELS_MINIMOS_DE_TEXTO"
  - "Rastreador.assinaturas_configuradas ligado em producao (Fase 1, plano 01-01)"
provides:
  - "l2scanner/aprendiz.py — o modulo novo, SEM RELOGIO, que conta LEITURAS e nunca segundos (D-09)"
  - "LEITURAS_PARA_APRENDER = 5 (a familia CARA da histerese assimetrica de Ajustes)"
  - "TETO_DE_CELULAS_TOLERADAS = 12, DERIVADO da tabela medida da Fase 1"
  - "ToleranciaAlemDoTeto — recusa de arranque, mensagem sem traceback, codigo 2"
  - "AjustesDoAprendiz (valida no __post_init__), Candidata, Aprendizado, RecusaPorInstabilidade, RetratoDasRecusas"
  - "distancia_de_hamming(a, b) -> int | None (None quando as formas diferem)"
  - "Aprendiz.observar(candidatas) -> ResultadoDoAprendiz; Aprendiz.retrato()"
  - "Observacao.mascaras_de_nome — SO PARA APRENDER, com tripwire de arquitetura"
  - "ResultadoDoTick.aprendizados e ResultadoDoTick.recusas_de_aprendizado"
  - "Sessao.aprendiz, Sessao._candidatas_para_aprender, Sessao._aprender, Sessao._registrar_recusas"
  - "config.ler_ajustes_do_aprendiz + a secao [identidade] do config.toml"
  - "O ELO: assinaturas_configuradas passa a ser ligado no PRIMEIRO aprendizado, com aviso da virada"
  - "aprendiz.py na tupla MODULOS do portao AST de relogio proprio"
affects:
  - "plano 02-02: a prova exaustiva do ramo da MARGEM (D-02) e o T-02-18 da confianca registrada"
  - "Fase 3 (batizar): herda Observacao.mascaras_de_nome e o Aprendizado estruturado; BATI-01/BATI-02"

actuals:
  tokens: 33460   # chars/4 sobre o diff realizado (133839 chars em l2scanner/, tests/ e config.toml)
  tasks: 3
  commits: 6

tech-stack:
  added: []   # zero dependencia nova: numpy ja estava; dataclasses, tomllib e logging sao stdlib
  patterns:
    - "Contador de estabilidade por CONTEUDO, com vigias descartados a cada leitura"
    - "Ancora da sequencia como referencia, e nunca a leitura anterior"
    - "Auto-diagnostico por RETRATO: log so quando o minimo ou o maximo muda"
    - "Constante DERIVADA, com a tabela medida e a CONDICAO DE VALIDADE ao lado do valor"

key-files:
  created:
    - "l2scanner/aprendiz.py"
    - "tests/test_aprendiz.py"
  modified:
    - "l2scanner/visao.py"
    - "l2scanner/sessao.py"
    - "l2scanner/config.py"
    - "l2scanner/__main__.py"
    - "config.toml"
    - "tests/test_acervo.py"
    - "tests/test_presenca.py"

key-decisions:
  - "As nove decisoes do CONTEXT implementadas sem reabrir nenhuma; zero checkpoint"
  - "A candidatura e `linha.nome is None`, e NUNCA `not linha.nome` — a string vazia significa 'reconheci e ninguem batizou'"
  - "Uma PRIMEIRA APARICAO nao e uma RecusaPorInstabilidade: recusa exige um vigia com quem comparar"
  - "O log.info do aprendizado sai ANTES do log.warning da virada, porque os dois caem no mesmo tick"
  - "A validacao do teto mora no __post_init__ e nao no leitor do config.toml"
  - "O except ToleranciaAlemDoTeto ficou num try LOCAL na leitura, e nao no bloco grande de main()"

patterns-established:
  - "Vigia por conteudo com ancora fixa: distancia de Hamming <= tolerancia INCREMENTA, maior REINICIA"
  - "Retrato acumulado (minimo, maximo, mediana) com emissao por MUDANCA, nunca a cada K"
  - "Perturbacao MEDIDA nos testes: afirmar distancia_de_hamming antes de afirmar o desfecho"
  - "Constante com CONDICAO DE VALIDADE escrita: a medida vale na faixa em que foi feita"

requirements-completed: [APRE-01, APRE-02]

coverage:
  - id: D1
    description: "Uma linha OCUPADA e NAO RECONHECIDA por N leituras seguidas com o recorte ESTAVEL faz o acervo ganhar EXATAMENTE uma entrada, SEM nome"
    requirement: APRE-01
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_a_enesima_leitura_grava_exatamente_uma_entrada_sem_nome"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_n_menos_uma_leitura_nao_grava_nada"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_continuar_rodando_nao_grava_mais_nada"
        status: pass
      - kind: integration
        ref: "tests/test_acervo.py#TestQuemConheceOAcervoEOQueOLacoFazComEle::test_o_laco_real_ESCREVE_no_acervo_e_escreve_uma_vez_so"
        status: pass
    human_judgment: false
  - id: D2
    description: "A linha recem-aprendida continua sem anunciar nada: zero eventos, identidade `#linhaN`, rotulo `Membro N`, com cal.nomes cheio de gente de verdade"
    requirement: APRE-01
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_a_linha_aprendida_continua_calada"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_o_elo_do_assinaturas_configuradas"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFatiaInteira::test_nada_e_despachado_e_nada_e_anunciado"
        status: pass
    human_judgment: false
  - id: D3
    description: "A virada de regime da party e DELIBERADA e AVISADA: antes do aprendizado a morte sai com o nome da lista por posicao, depois nao sai evento nenhum, e um log.warning sai UMA vez"
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAViradaDoRegimeDaParty::test_antes_morre_com_o_nome_da_lista_e_depois_nao_morre"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAViradaDoRegimeDaParty::test_o_aviso_da_virada_sai_uma_vez_so"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAViradaDoRegimeDaParty::test_o_aprendizado_e_registrado_ANTES_do_aviso_da_virada"
        status: pass
    human_judgment: true
    rationale: "A frase do aviso esta provada e a ordem das duas linhas tambem, mas se o texto que o usuario le no scanner.log da primeira sessao real explica a mudanca de regime bem o bastante para ele NAO concluir que o scanner quebrou, so um humano confere depois de uma sessao de verdade."
  - id: D4
    description: "A MESMA sequencia com o recorte MUDANDO entre as leituras nao grava NADA: instabilidade e recusada, e nao mediada nem tirada por mediana"
    requirement: APRE-02
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAInstabilidadeERecusada::test_o_recorte_que_muda_a_cada_leitura_nao_grava_nada"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAInstabilidadeERecusada::test_alternar_estavel_e_mudada_nunca_grava"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAInstabilidadeERecusada::test_a_instabilidade_nao_e_mediada"
        status: pass
    human_judgment: false
  - id: D5
    description: "A estabilidade e julgada pelo CONTEUDO e nunca pelo indice: duas pessoas na mesma posicao nunca somam, e a mesma pessoa que troca de posicao continua somando"
    requirement: APRE-02
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestOConteudoMandaENaoOIndice::test_a_mesma_pessoa_trocando_de_linha_continua_somando"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestOConteudoMandaENaoOIndice::test_duas_pessoas_na_mesma_linha_nunca_somam"
        status: pass
    human_judgment: false
  - id: D6
    description: "Toda recusa por instabilidade registra a DISTANCIA MEDIDA em celulas, junto da tolerancia vigente, no resultado E no scanner.log (D-07)"
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestARecusaDizQuantoMediu::test_a_recusa_chega_ao_resultado_do_tick_com_a_distancia_medida"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestARecusaDizQuantoMediu::test_o_mesmo_numero_sai_no_scanner_log_e_diz_o_que_fazer"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestARecusaDizQuantoMediu::test_trezentas_recusas_nao_viram_trezentas_linhas_de_resumo"
        status: pass
    human_judgment: false
  - id: D7
    description: "Cegueira nao ensina: com ui_visivel falso nenhum candidato existe, e a contagem CONGELA em vez de zerar"
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestCegueiraNaoEnsina::test_uma_sequencia_cega_inteira_nao_grava_nada"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestCegueiraNaoEnsina::test_a_cegueira_congela_a_contagem_em_vez_de_zerar"
        status: pass
    human_judgment: false
  - id: D8
    description: "Uma celulas_toleradas acima do TETO derivado da medida da Fase 1 e RECUSADA no arranque, com mensagem e sem traceback, por main() CHAMADA DE VERDADE"
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestARecusaAcontecENoARRANQUE::test_main_chamada_de_verdade_devolve_2_com_o_jogo_fechado"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestARecusaAcontecENoARRANQUE::test_um_config_bom_nao_impede_o_arranque"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAValidacaoDosAjustes::test_um_acima_do_teto_e_recusado"
        status: pass
    human_judgment: false
  - id: D9
    description: "aprendiz.py nao tem relogio proprio, esta na tupla MODULOS do portao AST, e nao importa visao, sessao, rastreador nem calibracao (D-09)"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_nenhum_now_de_datetime_na_arvore[aprendiz.py]"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_a_prova_pega_um_relogio_enfiado_em_CADA_modulo[aprendiz.py]"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestOAprendizNaoConheceOMundo::test_o_conjunto_de_irmaos_importados"
        status: pass
    human_judgment: false
  - id: D10
    description: "A mascara que o aprendiz consome viaja na Observacao e o rastreador.py NAO a le (T-02-08)"
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestORastreadorNaoLeAMascara::test_o_fonte_do_rastreador_nao_cita_a_mascara"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestORastreadorNaoLeAMascara::test_o_rastreador_nao_importa_o_aprendiz"
        status: pass
    human_judgment: false
  - id: D11
    description: "Portoes que impedem aprender lixo: linha VAZIA, linha ja reconhecida e anonima, recorte quase sem texto e casamento acima do limiar nunca viram entrada (T-02-02, T-02-03)"
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestQuemNuncaECandidato::test_uma_linha_vazia_nunca_e_candidata"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestQuemNuncaECandidato::test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestQuemNuncaECandidato::test_um_recorte_quase_sem_texto_nunca_vira_entrada"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestQuemNuncaECandidato::test_uma_candidata_que_ja_casou_acima_do_limiar_nao_aprende"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-08-31
status: complete
---

# Phase 2 Plan 01: Aprender Sozinho — Summary

**Nasce `l2scanner/aprendiz.py`: uma linha que ninguem reconhece, parada por cinco leituras com a imagem do nome estavel, vira sozinha uma entrada ANONIMA no acervo da Fase 1 — e continua exatamente tao calada quanto era, porque o mesmo tick que grava a primeira assinatura liga `assinaturas_configuradas` e avisa, uma vez, que o regime da party inteira mudou.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-08-31T08:24:25-03:00 (base a48caac)
- **Completed:** 2026-08-31T08:47:38-03:00
- **Tasks:** 3
- **Files modified:** 9 (2 criados, 7 modificados)

## Accomplishments

- **`l2scanner/aprendiz.py`**: modulo novo, SEM RELOGIO. Conta LEITURAS e nunca segundos, porque o tick nao e garantido e um replay tem de produzir o MESMO acervo que a sessao ao vivo produziu — num acervo IRREVERSIVEL a divergencia entre replay e campo nao seria um teste instavel, seria uma entrada permanente que ninguem consegue reproduzir para investigar.
- **Os tres portoes do `observar`, em ordem e cada um com razao propria.** (1) Recorte quase sem texto e descartado, e o motivo nao e obvio: com a lista de assinaturas VAZIA — a instalacao nova, que e onde esta fase mais importa — `identificar_linhas` retorna cedo e o portao de pixel de `_pontuar_mascara` nem chega a rodar, entao o do aprendiz e o UNICO que existe nesse caminho. (2) Confianca `>= LIMIAR_DE_CASAMENTO` CALA (D-02). (3) Casamento por conteudo contra a ANCORA da sequencia.
- **A ancora, e nao a leitura anterior.** Com tolerancia maior que zero, comparar cada leitura com a anterior deixaria uma deriva de uma celula por leitura somar N celulas ao longo da sequencia, e a sequencia seria chamada de estavel com a ultima leitura longe da primeira. O caso `test_a_ancora_e_a_referencia_e_a_deriva_nao_passa_por_baixo` afirma qual das duas o codigo faz: com tolerancia 3 e deriva de 2 por leitura, a quinta leitura esta a 8 da primeira e a sequencia e RECUSADA.
- **O ELO QUE O CRITERIO 1 EXIGIA.** Gravar a assinatura nao bastava: `Rastreador.assinaturas_configuradas` e calculado UMA vez no arranque e nasce `False` numa instalacao sem assinatura nenhuma. Sem o elo, a primeira pessoa aprendida seria gravada como ANONIMA no disco e ANUNCIADA COM O NOME DE OUTRA na tela — o defeito que a Fase 1 acabou de consertar, chegando por outra porta. Agora o mesmo tick que grava liga a flag.
- **E a virada nao e muda.** Ela muda o comportamento da party INTEIRA: `_rotular` passa a devolver "Membro N" para toda linha nao reconhecida e `_e_so_uma_posicao` passa a VETAR MORREU e RESSUSCITOU para toda identidade `#linhaN`. Para quem nunca calibrou assinatura mas preencheu `cal.nomes`, o efeito visivel e o scanner PARAR de anunciar mortes por nome no meio do farm. Um `log.warning` sai UMA vez, e um caso atravessando `Sessao` real afirma as duas metades da transicao.
- **A ordem das duas linhas de log foi corrigida na execucao** (ver Deviations): o `log.info` do aprendizado sai ANTES do `log.warning` da virada, porque as duas caem no MESMO tick e o log nao pode anunciar a consequencia antes da causa.
- **D-07 entregue como auto-diagnostico.** Cada recusa vai para `log.debug`; o RESUMO com a faixa medida (minimo, maximo e mediana), a tolerancia vigente e a acao — subir `[identidade] celulas_toleradas` — sai so quando o RETRATO MUDA. Por mudanca a emissao e auto-limitada e nao precisou de nenhum K inventado.
- **O teto e uma DERIVACAO, com a condicao de validade escrita.** `TETO_DE_CELULAS_TOLERADAS = 12` carrega a tabela medida da Fase 1 ao lado do valor, e diz em voz alta que os 48 pixels de texto sao a BASE da medida: num nick curto as mesmas 12 celulas sao 60% do sinal, e o teto protege contra o erro grosseiro sem prometer seguranca para todo nick.
- **A recusa acontece no ARRANQUE, provada por comportamento.** `main()` e CHAMADA DE VERDADE com um `config.toml` de `tmp_path` acima do teto e devolve 2, com `laco_principal` monkeypatchado para ACUSAR se a execucao chegar nele. Nenhum caso prova a recusa por inspecao da arvore sintatica: um `except` que existe nao e um `except` que recebe.
- **Zero alerta novo.** `resultado.despachos == []` e `resultado.eventos == []` no tick que aprendeu, afirmado.

## Task Commits

1. **Tarefa 1 (tracer, tdd): a fatia inteira — a linha desconhecida vira UMA entrada sem nome, e continua calada** — `70cd74d` (test, RED) + `e1a0e79` (feat, GREEN)
2. **Tarefa 2 (tdd): instabilidade e RECUSADA e nao mediada, e a recusa diz a distancia que mediu** — `473558c` (test, RED) + `c742308` (feat, GREEN)
3. **Tarefa 3 (tdd): o teto que vem da medida, e a tolerancia que o usuario consegue mexer** — `28bd42b` (test, RED) + `35290a1` (feat, GREEN)

## Files Created/Modified

- `l2scanner/aprendiz.py` — **criado.** `LEITURAS_PARA_APRENDER`, `TETO_DE_CELULAS_TOLERADAS`, `ToleranciaAlemDoTeto`, `AjustesDoAprendiz`, `Candidata`, `Aprendizado`, `RecusaPorInstabilidade`, `RetratoDasRecusas`, `ResultadoDoAprendiz`, `distancia_de_hamming`, `_Vigia`, `Aprendiz`. Importa so `acervo` e `identidade`; nao tem relogio.
- `tests/test_aprendiz.py` — **criado.** 63 casos: a fatia de ponta a ponta, o elo e a transicao avisada, a cegueira que congela, os quatro portoes de candidatura, o tri-estado do acervo, a instabilidade nas duas direcoes de D-08, a ancora contra a deriva, a distancia medida no resultado e no log, o retrato, o teto derivado, o leitor de configuracao e a recusa no arranque.
- `l2scanner/visao.py` — `Observacao.mascaras_de_nome` com o bloco de comentario no registro dos dois vizinhos "SO PARA MOSTRAR", e o preenchimento dentro de `extrair`. A funcao continua PURA.
- `l2scanner/sessao.py` — `ResultadoDoTick.aprendizados` e `.recusas_de_aprendizado`; `Sessao.aprendiz` com default `None`; `_candidatas_para_aprender`, `_aprender` e `_registrar_recusas`; os tres sinalizadores novos (`_ja_avisou_da_falha_do_aprendiz`, `_ja_avisou_da_virada_de_identidade`, `_ultimo_retrato_de_recusas`).
- `l2scanner/config.py` — `SECAO_DA_IDENTIDADE`, `_EXEMPLO_DA_IDENTIDADE`, `_inteiro_da_identidade` e `ler_ajustes_do_aprendiz`, no molde de `ler_watchlist_do_mercado`.
- `l2scanner/__main__.py` — a leitura da configuracao ANTES de qualquer fonte de captura, com o `try` local que devolve 2; o `Aprendiz` montado com a MESMA instancia de acervo da carga; `laco_principal` com o parametro novo; `aprendiz=` na `Sessao`.
- `config.toml` — a secao `[identidade]`, COMENTADA, com os dois numeros, o teto e a frase que fecha o circuito de D-07.
- `tests/test_acervo.py` — os dois portoes de fronteira de fase alterados pelo motivo que a docstring da Fase 1 ja mandava.
- `tests/test_presenca.py` — `"aprendiz.py"` na tupla `MODULOS` e o paragrafo do modulo novo na docstring.

## Registros exigidos pelo `<output>` do plano

**1. Contagem de testes:**

| Momento | Passaram | Skipped |
|---------|----------|---------|
| Linha de base (a48caac) | 3259 | 23 |
| Depois da Tarefa 1 | 3290 | 23 |
| Fim do plano | **3324** | 23 |

Delta: **+65** (63 casos novos em `tests/test_aprendiz.py`, 2 casos parametrizados novos em `tests/test_presenca.py` por conta do `aprendiz.py` na tupla). Nenhum teste existente foi afrouxado ou removido; os dois portoes de fronteira de fase foram alterados com a instrucao escrita na propria docstring deles. Os 23 skipped sao os mesmos da linha de base.

Nota: a `<precondition>` da Tarefa 1 previa "~3130 passando". A linha de base real do worktree e **3259**, porque a base `a48caac` ja traz ondas do workstream `mercado` posteriores a escrita do plano. A suite estava verde antes de comecar, que e o que a precondicao de fato exige.

**2. A distancia de Hamming REAL entre duas leituras do mesmo recorte: NAO HA, e o motivo esta medido.**

Nao existe medicao de campo, e a checagem foi feita em vez de assumida. As unicas duas capturas de party window versionadas sao `tests/fixtures/identidade/party_ordem_original.png` e `party_com_lider.png`, e elas sao **byte a byte identicas**:

```
pixels diferentes: 0 de 90828
np.array_equal(a, b) -> True
distancia de Hamming por linha: 0, 0, 0, 0  (mascaras de 80, 48, 24 e 60 pixels)
```

Ou seja, o "0" que sai dali nao e uma medida de ruido entre frames: e a mesma imagem comparada consigo mesma. `recordings/` e gitignored e nao se materializa num worktree nem num clone limpo, entao **nao ha nenhum par de leituras independentes do mesmo recorte no repositorio** — exatamente a ausencia que o CONTEXT descreveu ao fixar `celulas_toleradas` em zero.

O numero de campo virá do `scanner.log` da primeira sessao real, pela linha de resumo de D-07, e o comentario do `[identidade]` no `config.toml` diz onde acha-la. A Fase 3 nao deve tratar o zero acima como evidencia de que a tolerancia zero e suficiente em campo.

**3. Linhas de resumo produzidas pelo caso de 300 recusas:**

**UMA.** Com 300 chamadas alternando duas mascaras a 7 celulas de distancia, o `Aprendiz` acumulou 299 recusas (a primeira leitura nao e recusa: nao havia vigia com quem comparar) e o `scanner.log` recebeu **uma unica** linha de resumo:

```
RetratoDasRecusas(recusas=299, menor=7, maior=7, mediana=7.0)
LINHAS DE RESUMO: 1
  Nao aprendi assinatura nova por instabilidade: 1 recusa(s) nesta sessao, as leituras
  diferem de 7 a 7 celula(s), mediana 7.0, e a tolerancia atual e 0. Para o scanner
  aceitar essas leituras como a mesma pessoa, suba [identidade] celulas_toleradas no
  config.toml para um valor dentro dessa faixa. Este numero e medido na SUA tela, e nao
  um palpite.
```

O contador da linha diz "1" porque a linha e emitida no instante em que o retrato muda — a primeira recusa. Depois disso o minimo e o maximo nunca mais mudam e a emissao cala sozinha. T-02-10 cumprido sem escolher nenhum K.

**4. O conjunto observado pelo portao "quem conhece o acervo":**

```
['__main__.py', 'acervo.py', 'aprendiz.py']
```

`sessao.py` e `visao.py` continuam presos do lado de FORA, que sempre foi o ponto do portao: a sessao fala com o `aprendiz`, e nao com o acervo; a visao e uma funcao pura e nao fala com nenhum dos dois.

## Decisions Made

- **As nove decisoes do CONTEXT foram implementadas sem reabrir nenhuma.** Zero checkpoint, zero pergunta.
- **Uma PRIMEIRA APARICAO nao e uma `RecusaPorInstabilidade`.** Quando nao havia vigia nenhum sobrando com quem comparar, a candidata simplesmente comeca uma sequencia. Chamar isso de recusa poria, no retrato de D-07, um evento que nao mediu instabilidade nenhuma — e o retrato existe justamente para o usuario ler a faixa real das distancias. O caso de forma diferente (`distancia is None`) continua sendo uma recusa, porque ali HAVIA vigia e ele nao servia para comparar.
- **O vigia sai da mesa nos TRES desfechos de `gravar`.** Em `criado` e `ja_existia` porque a entrada existe; em `falhou` porque a proxima sequencia tem de comecar do zero, e nao repetir a gravacao a cada tick para sempre. `falhou` NAO conta como aprendido, exatamente como a docstring de `acervo.gravar` antecipou.
- **`_candidatas_para_aprender` e um metodo PURO.** Nao grava, nao registra e nao decide: so diz quem pode ser considerado. Isso e o que permite os casos de "linha vazia", "linha ja reconhecida e anonima" e "sem `ui_visivel`" rodarem sobre `Observacao` fabricada, sem frame e sem disco.
- **A validacao do teto mora no `__post_init__`, e nao no leitor.** O teto nao e pergunta de sintaxe de arquivo: e uma propriedade MEDIDA do reconhecedor, e ela vale para TODO caminho de construcao — inclusive um script ou um teste que nunca encoste no `config.toml`.
- **A recusa por faixa SOBE do leitor sem ser tratada.** Embrulhar `ToleranciaAlemDoTeto` em `AgendaInvalida` esconderia, atras de um erro de sintaxe, o unico erro daquela secao que fala de uma MEDIDA.
- **Um booleano nao passa por inteiro, e a checagem vem antes do `isinstance(int)`.** Em Python `True` E um `int` de valor 1, e `celulas_toleradas = true` viraria em silencio uma tolerancia de UMA celula.

## Deviations from Plan

### Correcao do revisor, aplicada durante a execucao

**1. A ordem das duas linhas de log no tick da virada**

- **Recebida antes da execucao**, e aplicada na Tarefa 1.
- **Issue:** o `log.warning` da virada de `assinaturas_configuradas` e o `log.info` do aprendizado saem no MESMO tick. Com o aviso primeiro, o `scanner.log` da primeira sessao real anunciaria a mudanca de regime da party ANTES de dizer o que a causou, e quem for ler o log procurando o motivo nao o acha, porque ele esta na linha de baixo.
- **Fix:** `Sessao._aprender` emite o `log.info` do aprendizado primeiro e so depois liga a flag e emite o `log.warning`. A ordem esta presa por teste (`test_o_aprendizado_e_registrado_ANTES_do_aviso_da_virada`), que le os niveis dos registros na ordem em que sairam e exige um INFO antes do primeiro WARNING.
- **Files modified:** `l2scanner/sessao.py`, `tests/test_aprendiz.py`
- **Committed in:** `e1a0e79`

### Auto-fixed Issues

**2. [Rule 3 - Blocking] O `except ToleranciaAlemDoTeto` nao podia morar no bloco grande de `main()`**

- **Found during:** Tarefa 3
- **Issue:** o plano manda acrescentar `except ToleranciaAlemDoTeto` "imediatamente ao lado de `BossInvalido` e `ConfiguracaoPerigosa`". Aquele `try` comeca em `return laco_principal(args, cal, ...)`, que fica DEPOIS do ramo `--mercado` e do `--testar-manutencao` — os dois constroem fonte de captura. A leitura da configuracao, por decisao do proprio plano, acontece ANTES de qualquer fonte de captura, entao a excecao seria levantada fora daquele `try` e subiria como traceback. O `except` existiria e nunca receberia nada: exatamente o defeito que a Tarefa 3 proibe provar por inspecao da arvore.
- **Fix:** o `try/except` ficou LOCAL, na propria linha da leitura, com o mesmo desfecho dos dois vizinhos (mensagem, sem traceback, `return 2`) e um comentario dizendo por que a posicao e diferente. O teste que exercita `main()` de verdade monkeypatcha `laco_principal` para ACUSAR se a execucao chegar nele, entao a recusa esta provada por comportamento e nao por topologia.
- **Files modified:** `l2scanner/__main__.py`
- **Verification:** `tests/test_aprendiz.py::TestARecusaAcontecENoARRANQUE` — os dois casos passam, e o caso de guarda contra prova vazia confirma que um `config.toml` bom nao impede o arranque e que os ajustes JA VALIDADOS descem para o laco pelo parametro.
- **Committed in:** `35290a1`

**3. [Rule 1 - Bug] Dois casos meus liam so o que vem DEPOIS do simbolo, e a documentacao do projeto vem ANTES**

- **Found during:** Tarefa 3
- **Issue:** os casos que afirmam a documentacao do teto (`aprendiz.py`) e do `[identidade]` (`config.toml`) fatiavam o arquivo a partir do simbolo. O idioma da casa e o comentario de bloco ANTES do valor (como em `identidade.py` e em `acervo.py`, e como toda secao do `config.toml`), entao o corte nao alcancava o texto que ele pretendia afirmar.
- **Fix:** os dois passaram a ler uma JANELA em volta do simbolo. A assercao nao mudou — os tres numeros, a condicao de validade e o `scanner.log` continuam exigidos, e a CO-LOCALIZACAO continua sendo o que esta preso. O helper `_bloco_do_teto` documenta a escolha.
- **Files modified:** `tests/test_aprendiz.py`
- **Committed in:** `35290a1`

### O que NAO foi feito, de proposito

- **Nenhum caso prova a recusa por inspecao da arvore sintatica**, conforme a proibicao explicita da Tarefa 3. O unico uso de `ast` em `tests/test_aprendiz.py` e o portao de imports do modulo (D-09), que e uma pergunta sobre topologia por natureza.
- **Nada foi despachado e nada foi anunciado.** Nenhum `_despachar`, nenhum evento novo, nenhuma linha nova no console.

## Known Stubs

Nenhum. Todos os simbolos declarados nesta fase tem implementacao e teste.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. O unico campo novo em objeto que atravessa camadas e `Observacao.mascaras_de_nome`, que ja e T-02-08 e nasceu com tripwire de arquitetura sobre o fonte do `rastreador.py`.

## Self-Check: PASSED

- `l2scanner/aprendiz.py` — presente (22936 bytes)
- `tests/test_aprendiz.py` — presente (64623 bytes)
- `.planning/workstreams/identidade/phases/02-aprender-sozinho/02-01-SUMMARY.md` — presente
- Os seis commits (`70cd74d`, `e1a0e79`, `473558c`, `c742308`, `28bd42b`, `35290a1`) existem no historico do worktree, na ordem RED/GREEN de cada tarefa.

## Notes for Next Phase

- **O plano 02-02 herda tudo o que precisa.** `Aprendizado.confianca` ja viaja e ja sai no `log.info` (T-02-18); a regra da MARGEM (D-02) esta implementada com um caso unitario, e a prova exaustiva do ramo e o trabalho dele.
- **O numero de campo ainda nao existe.** A primeira sessao real e que vai produzir a faixa de distancias no `scanner.log`. Ate la, nenhuma decisao sobre subir `celulas_toleradas` tem base medida — e o zero atual e a escolha certa por ausencia de evidencia, e nao por evidencia de suficiencia.
- **T-02-07 continua ACEITO e nao mitigado.** Um recorte contaminado pontua 0.0 contra tudo e pode ser aprendido se ficar N leituras parado. O `log.info` do aprendizado registra a contagem de pixels, que e o que torna o caso diagnosticavel depois. A Fase 3 deve tratar uma entrada nunca respondida como sinal.
