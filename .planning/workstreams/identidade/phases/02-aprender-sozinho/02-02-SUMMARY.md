---
phase: 02-aprender-sozinho
workstream: identidade
plan: 02
subsystem: identity
tags: [deduplicacao, correlacao, sha256, mutacao, fronteira-medida, tdd, party-window]

requires:
  - "02-01: l2scanner/aprendiz.py, Candidata, Aprendizado, Sessao._candidatas_para_aprender, Observacao.mascaras_de_nome"
  - "l2scanner/acervo.py — gravar tri-estado, carregar_identidades, chave_da_assinatura (Fase 1)"
  - "l2scanner/identidade.py — LIMIAR_DE_CASAMENTO, MARGEM_MINIMA_SOBRE_O_SEGUNDO, LIMIAR_DO_ORNAMENTO"
  - "tests/test_acervo.py — BITS_VIRADOS, quase_igual, semear, assinatura_da_linha, falhar_dentro_de"
provides:
  - "A familia APRE-04 completa em tests/test_aprendiz.py: 22 casos novos, os quatro caminhos fechados e o quinto documentado"
  - "A PRIMEIRA medida do projeto do drift que quebra a dedupe: 42 celulas -> 0.7531 (vale) / 43 celulas -> 0.7492 (nasce chave nova)"
  - "virar_celulas_no_frame — perturbacao EXATA do frame por brilho, deterministica, com a distancia de Hamming afirmada antes do desfecho"
  - "sem_icone — a pessoa sai da party sem derrubar ui_visivel, e sem virar cegueira"
  - "com_o_acervo_na_lista_viva — o reinicio afirmavel em tres linhas, sem subir processo"
  - "O portao que prende LIMIAR_DO_ORNAMENTO >= LIMIAR_DE_CASAMENTO, e o argumento de por que os dois portoes de candidatura se sobrepoem de proposito"
affects:
  - "Fase 3 (batizar): o par (42, 0.7531) / (43, 0.7492) e o pino que BATI-03 precisa; e uma sequencia de aprendizados com confianca em torno de 0.70 no scanner.log e a assinatura de T-02-18 em campo"
  - "Qualquer mexida em LIMIAR_DO_ORNAMENTO: baixa-lo abaixo de 0.75 reabre o caminho que D-02 hoje mascara"

actuals:
  tokens: 13620   # chars/4 sobre o diff realizado (54480 chars, 6d4da2f..015489f)
  tasks: 2
  commits: 2

tech-stack:
  added: []   # zero dependencia nova: numpy e cv2 ja estavam; os e pathlib sao stdlib
  patterns:
    - "Comparacao por CONJUNTO de chaves, e nunca por contagem: uma chave trocada por outra passa numa contagem"
    - "Verificacao dos portoes por MUTACAO do fonte, e nao por leitura: um portao que existe nao e um portao que recebe"
    - "Perturbacao do FRAME (e nao da mascara), por brilho, para atravessar recorte, mascara e identificar_linhas de verdade"
    - "Reinicio afirmado refazendo as tres linhas do arranque, sem subprocess"

key-files:
  created: []
  modified:
    - "tests/test_aprendiz.py"

key-decisions:
  - "Os helpers da Fase 1 sao IMPORTADOS de tests/test_acervo.py, e nao copiados: o 8 de BITS_VIRADOS foi medido e a tabela que o justifica mora no comentario dele"
  - "A linha usada em sai-e-volta e a ULTIMA ocupada (indice 3), porque extrair PARA no primeiro vao e apagar o icone de uma linha do meio derrubaria as de baixo junto"
  - "O caso de fronteira T-02-18 DOCUMENTA e nao conserta; ele afirma que uma segunda chave nasce, e a docstring diz as quatro razoes de isso ser aceito"
  - "As correlacoes de fronteira sao afirmadas com pytest.approx(abs=1e-3) e o LADO do limiar exigido exatamente: pinar o numero e o ponto, mas 4 casas de float entre versoes de OpenCV seria fragilidade sem ganho"
  - "Nenhum limiar novo, nenhum estado duravel novo, nenhuma assinatura publica alterada"

patterns-established:
  - "Contraste ANTES das afirmacoes de nao-acontecimento, em classe propria e no topo da familia"
  - "Premissas numericas medidas e afirmadas NA ORDEM em que sustentam o desfecho"
  - "Par de casos de fronteira (logo abaixo, logo acima) para delimitar a FAIXA em que uma garantia vale"
  - "Mutacao do fonte como verificacao de que um caso de prova nao e vacuo"

requirements-completed: [APRE-04]

coverage:
  - id: D14
    description: "A guarda contra prova vazia da familia inteira: a MESMA linha, com o acervo VAZIO, E aprendida em N leituras"
    requirement: APRE-04
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestOAcervoVazioAPRENDE_eEsteContrasteVemPrimeiro::test_a_MESMA_linha_com_o_acervo_VAZIO_e_aprendida"
        status: pass
    human_judgment: false
  - id: D15
    description: "Uma linha que casa com uma entrada do acervo, COM nome ou SEM, nao gera entrada nova: cem leituras estaveis deixam o CONJUNTO de chaves identico (criterio 3, T-02-13)"
    requirement: APRE-04
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAPessoaJaRECONHECIDA_NuncaViraUmaSegundaEntrada::test_uma_entrada_COM_NOME_casa_a_linha_e_cem_leituras_nao_gravam_nada"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAPessoaJaRECONHECIDA_NuncaViraUmaSegundaEntrada::test_uma_entrada_SEM_NOME_casa_a_linha_e_cem_leituras_nao_gravam_nada"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAPessoaJaRECONHECIDA_NuncaViraUmaSegundaEntrada::test_o_operador_e_o_PRIMEIRO_de_DOIS_portoes_e_nenhum_dos_dois_sobra"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestQuemNuncaECandidato::test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata"
        status: pass
    human_judgment: false
  - id: D16
    description: "A falha por MARGEM cala: com dois quase-duplicados no acervo, as quatro premissas sao medidas na ordem e cem leituras nao gravam nada; e o contraste dos tres desfechos mostra que a recusa e sobre a CONFIANCA (criterio 3, D-02, T-02-02)"
    requirement: APRE-04
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAFalhaPorMARGEM_Cala::test_as_quatro_premissas_sao_medidas_ANTES_do_desfecho"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFalhaPorMARGEM_Cala::test_cem_leituras_estaveis_nao_gravam_NADA"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFalhaPorMARGEM_Cala::test_os_TRES_desfechos_juntos_mostram_que_a_recusa_e_sobre_a_CONFIANCA"
        status: pass
    human_judgment: false
  - id: D17
    description: "O veto e sobre o NUMERO e nao sobre a origem: no limiar exato nao grava, um centesimo abaixo grava"
    requirement: APRE-04
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestOVetoESobreONumeroENaoSobreAOrigem::test_no_limiar_EXATO_nao_grava"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestOVetoESobreONumeroENaoSobreAOrigem::test_um_centesimo_ABAIXO_do_limiar_grava"
        status: pass
    human_judgment: false
  - id: D18
    description: "Sai da party e volta com o recorte DIFERENTE do gravado, na mesma sessao e depois de um reinicio, continua UMA entrada (criterio 4, D-03, T-02-14 parcial)"
    requirement: APRE-04
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestSaiEVoltaNaMesmaSessao::test_a_chave_da_volta_e_DIFERENTE_e_mesmo_assim_nada_novo_nasce"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestSaiEVoltaDepoisDoReinicio::test_o_acervo_lido_no_arranque_produz_o_MESMO_veto"
        status: pass
    human_judgment: false
  - id: D19
    description: "Reproduzir a mesma sequencia duas vezes, com e sem reinicio no meio, deixa exatamente o mesmo conjunto de chaves; e quatro linhas desconhecidas viram quatro chaves distintas (criterio 5)"
    requirement: APRE-04
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestOReplayNaoEngorda::test_a_party_inteira_desconhecida_vira_UMA_entrada_POR_PESSOA"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestOReplayNaoEngorda::test_a_MESMA_sequencia_de_novo_SEM_reinicio_nao_acrescenta_nada"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestOReplayNaoEngorda::test_a_MESMA_sequencia_de_novo_COM_reinicio_no_meio_tambem_nao"
        status: pass
    human_judgment: false
  - id: D20
    description: "Duas instancias sobre a mesma pasta produzem UMA entrada: uma recebe criado, a outra ja_existia, e o vigia da perdedora sai da mesa (DURA-03, T-02-16)"
    requirement: APRE-04
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestDuasInstanciasUmaEntrada::test_uma_recebe_criado_a_outra_ja_existia_e_a_pasta_fica_com_UMA_chave"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestDuasInstanciasUmaEntrada::test_quem_recebeu_ja_existia_nao_produz_aprendizado_na_leitura_seguinte"
        status: pass
    human_judgment: false
  - id: D21
    description: "falhou NAO conta como aprendido: nada entra na lista viva, assinaturas_configuradas nao liga, e a proxima sequencia tenta de novo e grava (T-02-15)"
    verification:
      - kind: integration
        ref: "tests/test_aprendiz.py#TestFalhouNaoMenteENaoPara::test_com_o_disco_fora_nada_entra_na_lista_viva_e_a_flag_nao_liga"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestFalhouNaoMenteENaoPara::test_a_proxima_sequencia_TENTA_DE_NOVO_e_com_o_disco_de_volta_grava"
        status: pass
    human_judgment: false
  - id: D22
    description: "A FRONTEIRA da dedupe esta documentada e nao escondida: 43 celulas de drift derrubam a correlacao para 0.7492 e uma SEGUNDA chave nasce, declarada CONHECIDA e ACEITA; 42 celulas dao 0.7531 e nenhuma nasce (T-02-18, disposicao accept)"
    verification:
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAFronteiraDaDedupe::test_o_invariante_que_faz_D02_bastar_ACIMA_do_limiar"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFronteiraDaDedupe::test_logo_ACIMA_do_limiar_a_dedupe_VALE_e_nenhuma_chave_nova_nasce"
        status: pass
      - kind: integration
        ref: "tests/test_aprendiz.py#TestAFronteiraDaDedupe::test_logo_ABAIXO_do_limiar_uma_SEGUNDA_chave_NASCE_e_isso_e_ACEITO"
        status: pass
      - kind: unit
        ref: "tests/test_aprendiz.py#TestAFronteiraDaDedupe::test_o_par_medido_que_o_SUMMARY_registra"
        status: pass
    human_judgment: true
    rationale: "Os numeros estao medidos e reproduziveis por comando, mas se 43 celulas de drift num nick de 60 pixels de texto e MUITO ou POUCO para uma sessao real de farm, so uma gravacao multi-frame de campo responde. E dessa resposta que depende a decisao de um segundo limiar."

duration: 41min
completed: 2026-08-31
status: complete
---

# Phase 2 Plan 02: Aprender Sozinho — A Mesma Pessoa Nao Vira Duas Entradas — Summary

**Os quatro caminhos por onde o acervo poderia engordar com repeticoes estao fechados e provados por comportamento; e o QUINTO, que esta fase nao fecha, esta medido em vez de escondido: uma pessoa que volta com 43 celulas de mascara diferentes correlaciona 0.7492 contra a propria entrada gravada, cai abaixo de 0.75, e ganha uma segunda entrada — enquanto 42 celulas dao 0.7531 e nada nasce. Uma unica celula separa a faixa em que a deduplicacao vale da faixa em que ela nao vale, e agora esse numero existe.**

## Performance

- **Duration:** ~41 min
- **Started:** 2026-08-31 (base `6d4da2f`, com a onda 02-01 ja mesclada)
- **Completed:** 2026-08-31
- **Tasks:** 2
- **Files modified:** 1 (`tests/test_aprendiz.py`; nenhum modulo de producao precisou mudar)

## Accomplishments

- **A familia APRE-04 completa, 22 casos novos, e nenhuma linha de producao alterada.** Este era um plano de PROVA, e a prova passou: `l2scanner/aprendiz.py` e `l2scanner/sessao.py` como a onda 1 os deixou ja atendem os quatro caminhos. O valor entregue nao e codigo novo, e a demonstracao de que o codigo existente faz o que a decisao diz.
- **O contraste vem primeiro, em classe propria.** `TestOAcervoVazioAPRENDE_eEsteContrasteVemPrimeiro` afirma que a MESMA linha, com o acervo vazio, E aprendida. Sem ele, todo "o conjunto de chaves nao mudou" abaixo passaria identico num cenario em que a candidatura nunca funcionou, e o arquivo estaria provando que a fase nao funciona com cara de estar provando o APRE-04.
- **Toda comparacao e por CONJUNTO de chaves.** Nunca por contagem. Uma chave trocada por outra — a assinatura de alguem substituida pela de outra pessoa — passaria em `len(chaves) == 1`, e num acervo sem comando de esquecer essa troca e permanente.
- **As premissas sao medidas ANTES do desfecho, na ordem em que o sustentam.** No caso do quase-duplicado sao quatro: chaves diferentes, as duas pontuacoes acima do limiar, a margem abaixo de 0.12, e a linha com `nome is None` e confianca alta. So depois vem "cem leituras nao gravaram nada".
- **Os tres desfechos juntos separam a causa do efeito.** Vazio APRENDE, uma entrada CALA, duas entradas CALAM. Sozinho, o terceiro seria compativel com a regra errada "se ha alguma coisa no acervo, nao aprenda". O do meio e o que mostra que as causas sao diferentes: com uma entrada a linha nem chega a ser candidata (`nome == ""`); com duas ela e candidata e e vetada pela CONFIANCA.
- **Os portoes foram verificados por MUTACAO, e nao por leitura.** Tres mutacoes rodadas no fonte: desligar D-03 derruba 5 casos, colapsar `falhou` em `criado` derruba 3, deixar o vigia vivo em `ja_existia` derruba 1. Um portao que existe nao e um portao que recebe, e a Fase 1 ja tinha registrado essa licao.
- **Achado do caminho, e ele muda como o criterio 5 deve ser lido:** os casos de REPLAY sozinhos NAO pegam D-03 desligado. Reproduzir o mesmo frame regrava a mesma chave deterministica e recebe `ja_existia`, entao a contagem nao muda nem sem a lista viva. Sao os casos de SAIR E VOLTAR, com a premissa de que a chave MUDOU, que prendem D-03. O criterio 5 e necessario e nao e suficiente.
- **A fronteira T-02-18 esta escrita com os quatro argumentos e os dois numeros**, e o caso irmao logo acima do limiar mostra a outra metade. Os dois vivem no mesmo arquivo de proposito, para ninguem ler o de cima sozinho e concluir que a dedupe vale sempre.
- **Zero dependencia nova, zero limiar novo, zero estado duravel novo.** Nenhuma assinatura publica mudou.

## Task Commits

1. **Tarefa 1 (tdd): o casamento contra o que ja esta gravado VETA, e nao apenas roda antes** — `a1287b7`
2. **Tarefa 2 (tdd): sai e volta, cai e sobe, roda duas vezes, e continua UMA entrada** — `015489f`

Os dois commits sao `test(...)` porque nenhum caso ficou vermelho contra o codigo de producao: nao houve fase GREEN a commitar. Ver *Deviations* para o que isso significa e para a unica correcao que a execucao exigiu.

## Registros exigidos pelo `<output>` do plano

### 1. As pontuacoes e a margem do quase-duplicado, e a distancia de Hamming do sai-e-volta

**O quase-duplicado** (linha 1 da fixture, `J4guar`, mascara `20x100` com **48 pixels de texto**, `BITS_VIRADOS = 8` importado da Fase 1):

| Medida | Valor |
|---|---|
| chaves diferentes | sim |
| pontuacao da entrada exata | **1.0000** |
| pontuacao da copia | **0.9212** |
| margem | **0.0788** |
| `MARGEM_MINIMA_SOBRE_O_SEGUNDO` | 0.12 |

A margem cai abaixo do minimo, `identificar_linhas` devolve `Casamento(None, 1.0000, 0.9212)`, e D-02 CALA. Os numeros batem exatamente com a medida da Fase 1 registrada no comentario de `BITS_VIRADOS`.

**O sai-e-volta** (linha 3 da fixture, `TioMad`, mascara `20x100` = **2000 celulas** com **60 pixels de texto**): a perturbacao usada e de **12 celulas**, distancia de Hamming **12** afirmada antes do desfecho, correlacao resultante **0.9075** contra a propria entrada gravada. Bem dentro da faixa em que a dedupe funciona, e a faixa foi escolhida de proposito — o criterio 4 e construido dentro dela, e o caso diz isso na docstring.

### 2. O PAR MEDIDO DA FRONTEIRA T-02-18 — a primeira medida de campo do drift

**Estes sao os numeros reais obtidos nesta execucao, e nao a previsao do plano.**

Linha 3 da fixture, mascara `20x100` (2000 celulas, 60 pixels de texto). A pessoa volta com N celulas da mascara viradas deterministicamente (`RandomState(42)`), e a correlacao e medida contra a assinatura que o proprio scanner gravou:

| celulas viradas | Hamming | pixels | correlacao | lado de 0.75 | nome da linha |
|---|---|---|---|---|---|
| 0 | 0 | 60 | 1.0000 | ACIMA | `""` |
| 1 | 1 | 61 | 0.9915 | ACIMA | `""` |
| 8 | 8 | 68 | 0.9374 | ACIMA | `""` |
| 12 | 12 | 70 | 0.9075 | ACIMA | `""` |
| 20 | 20 | 78 | 0.8578 | ACIMA | `""` |
| 40 | 40 | 98 | 0.7612 | ACIMA | `""` |
| **42** | 42 | 100 | **0.7531** | **ACIMA** | `""` |
| **43** | 43 | 101 | **0.7492** | **ABAIXO** | `None` |
| 50 | 50 | 108 | 0.7231 | ABAIXO | `None` |

**O par que o plano pediu:**

- **Logo ACIMA:** **42 celulas viradas -> correlacao 0.7531.** A linha e reconhecida (`nome == ""`), nao e candidata, e **nenhuma chave nova nasce**. A dedupe por correlacao VALE aqui.
- **Logo ABAIXO:** **43 celulas viradas -> correlacao 0.7492.** A linha perde o nome (`nome is None`), a confianca fica abaixo de `LIMIAR_DE_CASAMENTO`, ela volta a ser candidata, e **uma SEGUNDA chave nasce para a mesma pessoa**.

**A leitura desses numeros, para a Fase 3:**

- **Uma unica celula de mascara separa as duas metades.** A fronteira e uma LINHA, e nao uma zona cinzenta, e o caso `test_o_invariante_que_faz_D02_bastar_ACIMA_do_limiar` varre 0..59 celulas e prova por que: enquanto a linha TEM nome a confianca esta necessariamente acima de 0.75, e no instante em que ela perde o nome a confianca ja caiu abaixo. As duas metades se encaixam sem sobra e sem vao.
- **43 celulas sao 2.15% da mascara inteira, mas 71.7% do sinal de texto** (43 de 60 pixels). Este segundo numero e o que importa e o que a condicao de validade do `TETO_DE_CELULAS_TOLERADAS` ja antecipava: a fronteira e proporcional ao TAMANHO DO NICK, e nao ao tamanho do recorte. **Num nick curto ela chega muito mais cedo.** A medida acima vale para um nome de 60 pixels de texto e nao pode ser lida como universal.
- **A perturbacao usada acende celulas apagadas** (o recorte GANHA pixels: de 60 para 101). Isso e um modelo de drift, e nao o drift real: uma pessoa que volta com o fundo mais claro, ou com um efeito visual por cima, ganha pixels assim. Um drift que APAGA pixels de texto derrubaria a correlacao mais rapido, porque tira sinal em vez de acrescentar ruido. **A tabela e um limite otimista.**
- **O rastro em campo continua sendo `Aprendizado.confianca` no `log.info`** (entregue pela onda 1). Uma sequencia de aprendizados com confianca entre 0.70 e 0.75 e a assinatura deste caso acontecendo de verdade. Ate haver gravacao multi-frame de campo, nenhum segundo limiar tem base medida.

### 3. A contagem de testes

| Momento | Passaram | Skipped | Falharam |
|---------|----------|---------|----------|
| Linha de base (`6d4da2f`) | 3346 | 23 | 0 |
| Depois da Tarefa 1 | 3357 | 23 | 0 |
| **Fim do plano** | **3368** | **23** | **0** |

Delta: **+22**, todos em `tests/test_aprendiz.py` (11 na Tarefa 1, 11 na Tarefa 2). Nenhum teste existente foi editado, removido ou afrouxado. Os 23 skipped sao os mesmos da linha de base.

Nota sobre a linha de base: o dispatch previa "3367 passando / 2 pulados". A linha de base real do worktree e **3346 passando / 23 pulados**. A diferenca vem do ponto de merge, e nao de nada quebrado — a suite estava verde antes de comecar, que e o que a `<precondition>` da Tarefa 1 de fato exige.

### 4. O que ficou vermelho na primeira execucao, e qual foi o conserto

**Nenhum caso ficou vermelho contra o codigo de producao.** Os 22 casos passaram na primeira rodada. Num plano de PROVA isso e o desfecho esperado e nao um problema — mas tambem e exatamente a situacao em que uma suite verde pode nao estar provando nada. **Por isso a fase RED foi obtida por MUTACAO do fonte**, e e essa a informacao valiosa desta execucao:

| Mutacao aplicada | Casos que cairam | Veredito |
|---|---|---|
| `cal.assinaturas.append(...)` removido (D-03 desligado) | **5** | os casos de sai-e-volta e os quatro de fronteira |
| `falhou` colapsado em `criado` | **3** | os dois novos, mais o da onda 1 |
| `ja_existia` deixando o vigia na mesa | **1** | o caso dedicado da instancia perdedora |
| `>=` virando `>` no portao de D-02 | **1** | o caso do limiar exato |
| `linha.nome is None` virando `not linha.nome` | **1** | e AQUI esta o achado — ver abaixo |

**O achado, e ele contraria o que o plano previa.** O plano mandava escrever o caso da entrada anonima de modo que a troca de `linha.nome is None` por `not linha.nome` o fizesse "gravar uma entrada nova a cada N ticks". **Ele nao faz.** A mutacao foi rodada em vez de suposta, e o caso de ponta a ponta continua verde com o operador trocado.

A razao e estrutural. Com o operador trocado, a linha anonima volta a ser candidata em todo tick — mas chega ao `Aprendiz` com confianca alta, e o portao de D-02 a descarta antes de qualquer vigia nascer. E ela SEMPRE chega com confianca alta: so existem dois lugares em `identificar_linhas` que atribuem um nome, e os dois exigem pontuacao acima de um limiar — `LIMIAR_DE_CASAMENTO` (0.75) no primeiro passe e `LIMIAR_DO_ORNAMENTO` (0.85) na repescagem da coroa. Como **0.85 > 0.75**, "a linha tem nome" IMPLICA "a confianca passou de 0.75", que e precisamente a condicao que D-02 veta. Os dois portoes se sobrepoem por construcao.

**O conserto foi na PROVA, e nao no codigo:**

1. A mensagem de falha do caso de ponta a ponta foi corrigida. Ela afirmava um mecanismo falso ("se este caso gravou, o operador virou `not linha.nome`"), e uma mensagem que mente sobre a causa e pior do que nenhuma mensagem: ela manda quem depurar procurar no lugar errado.
2. Um caso novo, `test_o_operador_e_o_PRIMEIRO_de_DOIS_portoes_e_nenhum_dos_dois_sobra`, registra a medicao, prende a desigualdade `LIMIAR_DO_ORNAMENTO >= LIMIAR_DE_CASAMENTO` que faz o mascaramento existir, e afirma o operador na camada onde ele E observavel: `_candidatas_para_aprender`.
3. O caso que de fato prende o operador continua sendo o unitario da onda 1 (`TestQuemNuncaECandidato::test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata`), e foi ele — e so ele — que a mutacao derrubou.

**Por que isso importa alem da correcao de texto:** os dois portoes NAO sao redundantes por acidente, e nenhum pode ser removido como "limpeza". Tirar o portao do operador poe toda pessoa ja aprendida na mesa do aprendiz em todo tick, e a unica coisa entre ela e uma segunda entrada passa a ser um `>=` que o proprio arquivo demonstra ser sensivel a um centesimo. Tirar D-02 abre a porta da margem. E baixar `LIMIAR_DO_ORNAMENTO` abaixo de 0.75 um dia reabriria o caminho inteiro, em silencio — e agora ha um teste que cai se isso acontecer.

## Files Created/Modified

- `tests/test_aprendiz.py` — **modificado.** +1154 linhas. Imports novos (`os`, `l2scanner.acervo as mod_acervo`, `carregar_identidades`, `chave_da_assinatura`, `LIMIAR_DE_CASAMENTO`, `LIMIAR_DO_ORNAMENTO`, `MARGEM_MINIMA_SOBRE_O_SEGUNDO`, `_pontuar_mascara`, e os cinco helpers importados de `tests/test_acervo.py`). Nove classes novas e os helpers `pasta_do_acervo`, `chaves_do_acervo`, `com_o_acervo_na_lista_viva`, `pontuacoes_da_linha`, `virar_celulas_no_frame`, `sem_icone`, `assinatura_do_frame`, `aprender_a_ultima_linha`, mais a fixture `tres_conhecidas_menos_a_ultima` e as constantes medidas `CELULAS_DA_VOLTA`, `CELULAS_LOGO_ACIMA_DO_LIMIAR`, `CELULAS_LOGO_ABAIXO_DO_LIMIAR`.

Nenhum arquivo de producao foi tocado. Nenhum arquivo criado.

## Decisions Made

- **Os helpers da Fase 1 sao IMPORTADOS, e nao copiados.** `BITS_VIRADOS`, `quase_igual`, `semear`, `assinatura_da_linha` e `falhar_dentro_de` vem de `tests/test_acervo.py`. O 8 foi MEDIDO e a tabela que o justifica mora no comentario dele; duplicar o numero sem a medicao ao lado o transformaria, na primeira leitura de outra pessoa, de numero medido em constante inventada.
- **A linha de sai-e-volta e a ULTIMA ocupada (indice 3), e a escolha e mecanica.** `extrair` PARA no primeiro vao — a party window acaba ali — entao apagar o icone de uma linha do meio derrubaria junto todas as de baixo. Apagando o da ultima, so ela sai e as tres de cima continuam sendo lidas e reconhecidas, que e o que a party window faz quando alguem sai de verdade.
- **A pessoa "volta diferente" perturbando o FRAME, e nao a mascara.** Perturbar a mascara direto pularia `_recorte_do_nome`, `mascara_de_texto` e `identificar_linhas` — as tres pecas cuja tolerancia a ruido o criterio 4 afirma. A virada e por brilho porque a mascara e so um piso de brilho, o que torna a perturbacao EXATA: o numero de celulas pedido e o numero virado, afirmado por `distancia_de_hamming` antes de qualquer desfecho.
- **O reinicio nao sobe processo, e a docstring diz por que.** O arranque real faz tres coisas com o acervo, e `com_o_acervo_na_lista_viva` refaz as tres. Um `subprocess` acrescentaria captura de tela, relogio e sistema de arquivos reais a um caso cuja pergunta — quem esta na lista viva depois do arranque — nao depende de nenhum dos tres. Escrito na docstring para ninguem "melhorar" isso depois.
- **As correlacoes de fronteira sao afirmadas com `pytest.approx(abs=1e-3)`, mas o LADO do limiar e exigido exatamente.** Pinar o numero e o ponto do caso; exigir quatro casas de float entre versoes de OpenCV seria fragilidade sem ganho. O que nao pode escorregar e de que lado de 0.75 cada um cai, e isso e afirmado sem tolerancia.
- **A varredura da fronteira afirma o numero de celulas exato (43) com mensagem propria**, dizendo que ele nao e um teste a afrouxar: e o numero que a Fase 3 vai usar. Se ele mudar, alguem mudou o comportamento do reconhecedor.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A mensagem de falha do caso da entrada anonima afirmava um mecanismo falso**

- **Found during:** Tarefa 1, na verificacao por mutacao.
- **Issue:** o plano previa que o caso de ponta a ponta cairia com `not linha.nome` no lugar de `linha.nome is None`, e a mensagem de falha dizia isso. A mutacao foi rodada e o caso NAO cai: D-02 mascara a troca, porque `LIMIAR_DO_ORNAMENTO` (0.85) e maior que `LIMIAR_DE_CASAMENTO` (0.75) e portanto "a linha tem nome" implica "a confianca passou de 0.75". Uma mensagem de falha que aponta a causa errada manda quem depurar procurar no lugar errado, e num arquivo cujo proposito e ser lido daqui a meses isso e um defeito e nao um detalhe.
- **Fix:** mensagem corrigida para afirmar so o que o caso prova; caso novo `test_o_operador_e_o_PRIMEIRO_de_DOIS_portoes_e_nenhum_dos_dois_sobra` acrescentado com a medicao, o argumento estrutural, o portao sobre a desigualdade dos dois limiares, e a afirmacao do operador na camada onde ele e observavel.
- **Files modified:** `tests/test_aprendiz.py`
- **Verification:** os dois casos passam; a mutacao `not linha.nome` derruba o unitario da onda 1, como agora esta escrito que derruba.
- **Committed in:** `a1287b7`

### Desvio de forma, e nao de conteudo

**2. Os dois commits sao `test(...)`, e nao pares RED/GREEN**

- O plano e de PROVA e diz em voz alta: "so mexa em `l2scanner/aprendiz.py` se algum deles ficar vermelho". Nenhum ficou. Nao havendo conserto de producao, nao ha commit `feat`/`fix` a fazer, e inventar um seria ruido no historico.
- A disciplina RED foi cumprida por outro meio, mais forte para este caso: **cada portao teve o fonte MUTADO e a queda verificada** (tabela na secao 4 acima). Um caso de prova que nunca foi visto falhando nao e um caso de prova, e a mutacao e o que fecha esse buraco quando o codigo ja esta certo.

### O que NAO foi feito, de proposito

- **O caso de fronteira T-02-18 nao foi "consertado".** Transforma-lo num nao-aprendizado inventaria o segundo limiar que nao ha como calibrar; simplesmente nao escreve-lo deixaria a suite verde afirmando uma dedupe sem faixa. Documentar a fronteira, com as premissas medidas, foi a terceira opcao e e a honesta.
- **Nenhum limiar novo em `aprendiz.py`.** `LIMIAR_DE_CASAMENTO` e `MARGEM_MINIMA_SOBRE_O_SEGUNDO` ja existem, ja foram medidos e ja governam esta decisao.
- **Nenhum estado duravel novo.** Nada de arquivo de controle, nada de "ja aprendi isto nesta sessao" em disco (T-02-17). A memoria da fase E o acervo.
- **As duas capturas de party window versionadas nao foram usadas como evidencia de estabilidade.** O 02-01-SUMMARY mediu e registrou que `party_ordem_original.png` e `party_com_lider.png` sao BYTE A BYTE identicas: comparar as duas mede uma imagem consigo mesma, e nao ruido entre frames. Toda perturbacao desta onda e SINTETICA e declarada como tal.

## Issues Encountered

Nenhum bloqueio. Nenhum checkpoint. Nenhuma pergunta ao usuario.

## Known Stubs

Nenhum. Todos os casos declarados neste plano existem, rodam e afirmam comportamento.

## Threat Flags

Nenhuma superficie nova. Este plano nao acrescentou codigo de producao, nao criou arquivo, nao abriu porta de rede e nao instalou pacote. `T-02-SC` permanece `accept` sem nada a auditar.

**Atualizacao ao registro STRIDE do plano:**

- **T-02-02** (aprender um quase-duplicado): **mitigate, cumprido.** As quatro premissas medidas antes do desfecho, mais o contraste dos tres desfechos.
- **T-02-13** (`not linha.nome`): **mitigate, cumprido, com a nota de que a defesa efetiva e DUPLA.** O caso unitario da onda 1 prende o operador; D-02 mascara a troca no desfecho de ponta a ponta. A sobreposicao agora esta documentada e presa por teste.
- **T-02-14** (reaprender quem saiu e voltou): **partial, e continua partial** — como o plano ja dizia. Vale ACIMA de 0.75, medido ate 42 celulas de drift.
- **T-02-15**, **T-02-16**, **T-02-17**: **mitigate, cumpridos**, cada um com caso dedicado e mutacao verificada (exceto T-02-17, que e uma ausencia e foi conferida por inspecao do diff: nenhum arquivo novo, nenhuma escrita fora do acervo).
- **T-02-18** (volta abaixo de 0.75): **accept, DOCUMENTADO E MEDIDO.** O par (43 celulas, 0.7492) / (42 celulas, 0.7531) e a primeira medida do projeto. Reavaliar quando houver gravacao multi-frame de campo.

## User Setup Required

Nenhum. Nada a instalar, nada a configurar, nada a rodar. Os criterios 3, 4 e 5 sao demonstraveis por `python -m pytest tests/test_aprendiz.py -q` com o jogo fechado e sem rede.

## Next Phase Readiness

- **APRE-01, APRE-02 e APRE-04 estao completos.** Somados aos criterios 1 e 2 da onda 02-01, os cinco criterios da Fase 2 estao cobertos.
- **O pino que a Fase 3 pediu existe:** o par (42 celulas -> 0.7531) / (43 celulas -> 0.7492), com a ressalva de que **71.7% do sinal de texto** e a leitura que generaliza, e nao os 2.15% da mascara. Num nick curto a fronteira chega antes.
- **A decisao sobre um segundo limiar continua SEM base medida**, e essa e a conclusao honesta desta onda. O que existe agora e um numero de laboratorio e um modelo de drift otimista (que acende celulas em vez de apagar). O numero de campo so sai de uma gravacao multi-frame real, e ate la o `log.info` de cada aprendizado, com a confianca, e o unico instrumento.
- **Um sinal concreto para a Fase 3:** uma entrada do acervo que nunca e respondida no batismo, somada a outra entrada da mesma sessao com confianca entre 0.70 e 0.75 no `scanner.log`, e a assinatura de T-02-18 tendo acontecido. As duas entradas sao a MESMA pessoa, e o batismo perguntaria duas vezes por ela.
- **Uma armadilha herdada, escrita para nao se perder:** se alguem baixar `LIMIAR_DO_ORNAMENTO` abaixo de `LIMIAR_DE_CASAMENTO`, o mascaramento que hoje protege o caminho do operador desaparece. `test_o_operador_e_o_PRIMEIRO_de_DOIS_portoes_e_nenhum_dos_dois_sobra` cai se isso acontecer, e a mensagem dele explica o porque.

## Self-Check: PASSED

- `tests/test_aprendiz.py` — presente, 118527 bytes, 2794 linhas, 85 casos (63 da onda 1 + 22 desta).
- `.planning/workstreams/identidade/phases/02-aprender-sozinho/02-02-SUMMARY.md` — presente.
- Os dois commits (`a1287b7`, `015489f`) existem no historico do worktree.
- `python -m pytest tests/ -q` -> **3368 passed, 23 skipped**, 0 falhas.
- Nenhum arquivo de producao modificado: `git diff 6d4da2f..HEAD --numstat` lista **um** arquivo, `tests/test_aprendiz.py`.
