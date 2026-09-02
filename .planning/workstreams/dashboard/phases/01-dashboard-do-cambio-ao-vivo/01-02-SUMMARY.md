---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 02
subsystem: api
tags: [csv, fraction, median_low, precedencia-de-estados, tdd, copywriting-contract]

requires:
  - phase: 01-01
    provides: "ArquivoRecortado, LeituraAoVivo, observacoes_ao_vivo e o payload minimo do tracer"
provides:
  - "LeituraAoVivo.linhas_completas — a contagem de REGISTROS que alimenta a frase de prova do estado vazio"
  - "NOTA_DE_LINHA_PARCIAL e as dez constantes de frase copiadas do ## Copywriting Contract"
  - "PontoDaSerie e pontos_por_instante — CTX-1 literal, com a refutacao da recomendacao da pesquisa no fonte"
  - "LARGURAS_DE_BALDE, ancora_da_meia_noite, baldes — agregacao sem float e sem valor inventado"
  - "ESTADOS, LIMIAR_DE_FRESCOR, serie_para_o_grafico, payload(pasta, agora, cambio=None)"
  - "frase_de_piso_do_menor / frase_de_piso_da_tipica — o ponto de decisao unico que o 01-01-SUMMARY pediu"
  - "O contrato de cambio por FORMA (reais_por_xm, informado_em), sem import de dashboard_cambio"
affects: [01-04, 01-05, 01-06, 01-07, 01-08]

actuals:
  tokens: 21550
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Derivar a segunda decisao da PRIMEIRA em vez de repetir o criterio: `_e_a_taxa` compara a identidade da funcao devolvida por `formatador_do_unitario` em vez de reescrever o `if` da sentinela"
    - "Fronteira de tipo declarada num lugar so, com o erro MEDIDO ao lado (`_pixel`, 1,9e-11)"
    - "Proibicao verificada por TOKEN quando a verificacao por substring reprova valor legitimo"
    - "Precedencia de estados como tupla ordenada com a razao da ORDEM escrita, e teste de EMPATE ao lado dos testes de cada estado"

key-files:
  created:
    - tests/test_dashboard_leitura.py
    - tests/test_dashboard_dados.py
  modified:
    - l2scanner/dashboard_dados.py

key-decisions:
  - "CTX-1 implementado literalmente: um ponto e UM instante, e a ausencia da mediana e o caminho NORMAL — a recomendacao (b) da pesquisa esta refutada na docstring de pontos_por_instante, com a medicao e a data da recusa"
  - "`0,00` saiu de FRASES_PROIBIDAS: por substring ela reprova `30,00`, medido. A proibicao virou sonda por TOKEN no teste, com controle"
  - "linhas_completas conta REGISTROS e nao linhas do arquivo — a frase de prova poe duas contagens lado a lado e elas tem de ser da mesma especie"
  - "`series` traz TODAS as series do arquivo, e nao so a da Adena: filtrar aqui seria o `if` da Adena que o DASH-05 recusa"
  - "O destaque usa a serie INTEIRA (a conta do console, DASH-03) e o grafico usa o instante (CTX-1) — sao perguntas diferentes, e a diferenca esta escrita na docstring de payload"
  - "Duas frases de piso e nao uma com sinalizador, espelhando as duas redacoes do console, presas por substring contra as linhas dele"

patterns-established:
  - "Controle ao lado de toda assercao de ausencia: cauda completa, ancora arbitraria, sonda do zero, tripwire olhando fonte que de fato abre arquivo"
  - "O dublê de contrato por FORMA para um modulo que esta sendo escrito em paralelo, com a razao do nao-import escrita nele"

requirements-completed: [DASH-01, DASH-03, DASH-04, DASH-05]

coverage:
  - id: D1
    description: "300 leituras do CSV nao mudam tamanho, mtime_ns nem sha256 — e o fonte das duas funcoes que tocam disco nao contem modo de escrita nem criacao de pasta"
    requirement: DASH-01
    verification:
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestALeituraNaoEscreveNADA::test_TREZENTAS_leituras_nao_mudam_um_BYTE_do_arquivo"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestALeituraNaoEscreveNADA::test_o_fonte_de_observacoes_ao_vivo_nao_tem_MODO_DE_ESCRITA"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestALeituraNaoEscreveNADA::test_o_fonte_de_ArquivoRecortado_open_nao_tem_MODO_DE_ESCRITA"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestOPortaoDeContratoEOMESMO::test_a_leitura_NAO_CRIA_o_arquivo_ausente"
        status: pass
    human_judgment: false
  - id: D2
    description: "A cauda cortada degrada para a ultima linha completa, com CONTROLE NEGATIVO provando que `cauda_incompleta` nao e constante"
    requirement: DASH-01
    verification:
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestACaudaIncompletaCaiSOZINHA::test_o_corte_no_MEIO_da_ultima_linha_devolve_as_COMPLETAS"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestACaudaIncompletaCaiSOZINHA::test_CONTROLE_NEGATIVO_texto_terminado_em_quebra_tem_cauda_COMPLETA"
        status: pass
    human_judgment: false
  - id: D3
    description: "Uma linha ruim cai sozinha e o aviso NOMEIA o numero dela; as demais carregam"
    requirement: DASH-01
    verification:
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestUmaLinhaRuimCaiSOZINHA::test_o_aviso_NOMEIA_o_numero_da_linha_descartada"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_leitura.py#TestUmaLinhaRuimCaiSOZINHA::test_as_demais_linhas_carregam_NORMALMENTE"
        status: pass
    human_judgment: false
  - id: D4
    description: "Um ponto do grafico e UM instante (CTX-1): a mediana e nula abaixo do piso, com faltam=3, e a evidencia viaja dentro do ponto"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestUmPontoEUmINSTANTE::test_um_instante_com_DUAS_ofertas_tem_menor_mas_a_tipica_e_NULA"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestUmPontoEUmINSTANTE::test_um_instante_com_CINCO_ofertas_tem_tipica_que_ESTEVE_na_lista"
        status: pass
    human_judgment: false
  - id: D5
    description: "Nenhum balde inventa valor (D-02), o indice e inteiro e a ancora e a meia-noite local — com controle de ancora arbitraria"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestOBaldeNuncaInventaVALOR::test_o_valor_de_CADA_balde_esta_CONTIDO_na_lista_dos_instantes_dele"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestOBaldeNuncaInventaVALOR::test_duas_leituras_do_MESMO_dia_civil_caem_no_MESMO_balde_de_um_dia"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestOBaldeNuncaInventaVALOR::test_CONTROLE_com_ancora_arbitraria_o_MESMO_dia_se_PARTE_em_dois"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestNadaNaAgregacaoDevolveFLOAT::test_o_valor_de_todo_balde_e_Fraction_e_nunca_float"
        status: pass
    human_judgment: false
  - id: D6
    description: "A precedencia dos cinco estados e fechada e testada uma a uma, mais o EMPATE (cabecalho quebrado E sem Adena vence o erro de contrato)"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAPrecedenciaDosCincoESTADOS::test_EMPATE_cabecalho_quebrado_E_sem_adena_vence_o_ERRO_DE_CONTRATO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAPrecedenciaDosCincoESTADOS::test_os_ESTADOS_sao_CINCO_na_ordem_do_UI_SPEC"
        status: pass
    human_judgment: false
  - id: D7
    description: "A serie e um ELEMENTO de lista com contrato fixo: duas series produzem dois elementos com o conjunto de chaves identico (DASH-05 estrutural)"
    requirement: DASH-05
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestASerieEUmElementoDeLista::test_duas_series_produzem_DOIS_elementos_com_as_MESMAS_chaves"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestASerieEUmElementoDeLista::test_a_serie_de_um_item_comum_sai_em_OUTRA_unidade_que_a_da_adena"
        status: pass
    human_judgment: false
  - id: D8
    description: "Nenhum valor padrao e chutado: sem cambio o sub-objeto de R$ e nulo e a frase de indisponivel viaja nos avisos; com cambio o R$ vem marcado como derivado e carimbado"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestNenhumValorPadraoEChutado::test_SEM_cambio_o_sub_objeto_de_reais_e_NULO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestNenhumValorPadraoEChutado::test_COM_cambio_o_real_aparece_DERIVADO_e_com_carimbo"
        status: pass
    human_judgment: false
  - id: D9
    description: "Dado velho perde a afirmacao de 'agora' e NAO o numero; e nenhuma frase proibida aparece em nenhum dos cinco estados"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestODadoVelhoPerdeOAgoraENaoONumero::test_recencia_ACIMA_do_limiar_marca_velho_e_MANTEM_o_numero"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAsFrasesProibidasNaoAparecem::test_nenhuma_frase_proibida_em_NENHUM_dos_cinco_estados"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAsFrasesProibidasNaoAparecem::test_CONTROLE_a_sonda_do_zero_ACUSA_um_zero_de_verdade"
        status: pass
    human_judgment: false
  - id: D10
    description: "A fronteira do float existe num lugar so: o ponto carrega o pixel em float E a verdade em string, e a ausencia vira nulo e nunca zero"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAFronteiraDoFLOAT::test_o_ponto_carrega_o_pixel_em_float_E_a_verdade_em_string"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAFronteiraDoFLOAT::test_sem_valor_o_pixel_e_NULO_e_nao_zero"
        status: pass
    human_judgment: false
  - id: D11
    description: "A frase de piso do payload e a MESMA do console, presa por substring contra `_linha_do_menor` e `_linha_da_mediana`"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAFraseDePisoEAMESMADoConsole::test_a_frase_do_menor_e_SUBSTRING_da_linha_do_console"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_dados.py#TestAFraseDePisoEAMESMADoConsole::test_a_frase_da_tipica_e_SUBSTRING_da_linha_do_console"
        status: pass
    human_judgment: false

duration: 38min
completed: 2026-09-01
status: complete
---

# Phase 01 Plan 02: A camada de dado do dashboard Summary

**A leitura ao vivo com as tres provas do DASH-01 presas em teste (impressao digital em 300 leituras, degradacao com controle negativo, linha ruim nomeada no log), a agregacao que implementa CTX-1 literalmente — um ponto e um instante, e a mediana ausente e o caminho NORMAL — e o payload com a precedencia fechada dos cinco estados, `Fraction` ate a fronteira do JSON e a serie como elemento de lista.**

## Performance

- **Duration:** 38 min
- **Tasks:** 3 de 3 (todas `tdd="true"`, RED e GREEN separados)
- **Files modified:** 3 (2 criados, 1 alterado)
- **Suite:** **4.566 passed, 25 skipped**, 0 falhas (era 4.517 antes do plano)

## Accomplishments

- **As tres provas do DASH-01 estao presas, cada uma com o seu controle.** A impressao digital de tres componentes em **300** leituras; a degradacao para a ultima linha completa com um **CONTROLE NEGATIVO** que exige `cauda_incompleta` FALSO num texto terminado em quebra de linha (sem ele, um `True` constante deixaria os quatro cortes verdes); e o aviso que **NOMEIA o numero da linha**, capturado por `caplog`. Mais um tripwire por `inspect.getsource` sobre `observacoes_ao_vivo` **e** sobre `ArquivoRecortado.open`, este ultimo com um controle que exige o fonte conter de fato uma abertura de leitura — sem ele, renomear a funcao deixaria a assercao verde sobre uma cadeia vazia.
- **CTX-1 foi implementado literalmente, e a recomendacao contraria esta refutada NO FONTE.** A docstring de `pontos_por_instante` carrega a medicao inteira (92 observacoes, 13 instantes distintos, a maior serie com 2, `N_MINIMO_PARA_MEDIANA = 5`), a recomendacao (b) da pesquisa, a data da recusa do usuario, e a frase que fecha o assunto: a ausencia da mediana e o caso **NORMAL** desta tela, e quem achar que "esta faltando dado" tem de ler o paragrafo antes de consertar.
- **Nenhum balde inventa valor, e isso e um `assert in` e nao uma intencao.** Para cada balde produzido, o teste afirma que o valor esta **CONTIDO** na lista dos valores dos instantes dele. `median`, `mean` e `median_high` continuariam devolvendo um numero plausivel e do tamanho certo — so o `assert in` os pega. As duas medicoes que sustentam as escolhas (`13/42` fora da lista; `69713.696` contra `69713`) estao escritas ao lado do codigo que as executa.
- **A precedencia dos cinco estados e fechada, testada uma a uma, e com um teste de EMPATE.** Um arquivo com cabecalho trocado tambem nao tem serie da Adena; o teste monta exatamente esse caso e afirma que vence o erro de contrato. A razao da ORDEM esta escrita: e a gravidade da ignorancia, de "o arquivo nao e mais este arquivo" ate "ha o que mostrar".
- **O DASH-05 ficou estrutural do lado do dado.** `series` e sempre uma LISTA, a palavra `adena` nao aparece no corpo de `serie_para_o_grafico`, e a unidade e a escala do eixo sao **derivadas** de `formatador_do_unitario` em vez de repetirem o `if` da sentinela — o teste monta duas series e afirma dois elementos com o conjunto de chaves identico.
- **Uma refutacao NOVA foi medida e escrita** — ver "Deviations from Plan" abaixo: a proibicao do `0,00` por substring reprova `30,00`.

## Task Commits

1. **Tarefa 1: as tres provas do DASH-01 — RED** — `aff569c` (test)
2. **Tarefa 1: a leitura endurecida — GREEN** — `1289dff` (feat)
3. **Tarefa 2: a agregacao — RED** — `cc1f86d` (test)
4. **Tarefa 2: pontos, baldes e ancora — GREEN** — `29bca76` (feat)
5. **Tarefa 3: o payload — RED** — `f0c781c` (test)
6. **Tarefa 3: a precedencia fechada — GREEN** — `bbc2640` (feat)

_As tres tarefas sao `tdd="true"` e por isso tem dois commits cada (RED e GREEN). Nao houve REFACTOR em nenhuma: o codigo saiu do GREEN sem duplicacao a remover._

## Files Created/Modified

**Criados**
- `tests/test_dashboard_leitura.py` — 14 testes: o portao de contrato, os quatro cortes de cauda mais o controle negativo, a linha ruim nomeada, e a impressao digital com os dois tripwires
- `tests/test_dashboard_dados.py` — 35 testes: agregacao (14) e payload (21), incluindo a varredura recursiva de frases proibidas nos cinco estados e o dublê de cambio por FORMA

**Alterado**
- `l2scanner/dashboard_dados.py` — `LeituraAoVivo.linhas_completas`, as dez constantes de frase do `## Copywriting Contract`, `PontoDaSerie`, `pontos_por_instante`, `LARGURAS_DE_BALDE`, `ancora_da_meia_noite`, `baldes`, `frase_de_piso_do_menor`/`frase_de_piso_da_tipica`, `_e_a_taxa`/`_escala_do_grafico`/`_pixel`, `serie_para_o_grafico`, `ESTADOS`, `LIMIAR_DE_FRESCOR`, `_valor_em_reais` e o `payload` com a precedencia fechada

## Decisions Made

- **`_e_a_taxa` DERIVA em vez de repetir.** A unidade exibida e a escala do eixo precisam saber se a serie e a da Adena. A rota obvia seria `if chave == CHAVE_DA_SERIE_DA_ADENA`, e ela seria o terceiro `if` sobre a sentinela — precisamente o que a docstring de `formatador_do_unitario` existe para nao ter ("no dia em que um divergisse, a tela imprimiria `0,00 por unidade` para a Adena com toda a confianca do mundo"). A escolhida compara a **identidade da funcao devolvida** por `formatador_do_unitario`: se o criterio mudar la, muda aqui junto, sem ninguem precisar lembrar.
- **`series` traz TODAS as series do arquivo.** Filtrar so a Adena aqui seria o `if` da Adena que o DASH-05 recusa. Quais series a pagina instancia e decisao da pagina (01-06/01-07); o dado oferece o que conhece. O destaque continua sendo so da Adena, porque a pergunta do destaque e "quanto vale 1 milhao de adena".
- **O destaque usa a serie INTEIRA e o grafico usa o instante.** Nao e inconsistencia: sao perguntas diferentes. O destaque tem de bater com o console (DASH-03, e o console chama `menor_pedido_visivel` sobre `observacoes_de(chave)`); o grafico agrupa por instante porque um ponto e um instante (CTX-1). A distincao esta escrita na docstring de `payload` para nao ser "consertada" depois.
- **Duas frases de piso, e nao uma com sinalizador.** O console tem duas redacoes (o menor sem `faltam`, a mediana com). Espelhar UMA das duas em ambos os lugares faria a tela discordar do terminal para um dos dois numeros. O molde e o de `formatar_taxa_derivada`/`formatar_unitario_derivado`: "duas funcoes com nomes diferentes sao duas coisas que ninguem confunde por omissao". Isso atende o pedido explicito do `01-01-SUMMARY` de transformar a frase duplicada em ponto de decisao unico **antes** dela ganhar o segundo chamador — e ha dois testes prendendo cada uma por substring contra a linha do console.
- **`linhas_completas` conta REGISTROS, e nao linhas do arquivo.** A frase de prova poe duas contagens lado a lado ("N linhas, M da serie"), e as duas tem de ser da mesma especie. O `01-UI-SPEC.md` ilustra a frase com `93`, que e a contagem de LINHAS do arquivo de campo (cabecalho incluido); o payload informa as **92 de DADO**. Incluir o cabecalho de um lado e contar observacoes do outro seria comparar coisas diferentes com a mesma palavra. A divergencia esta escrita ao lado da constante.
- **O contrato de cambio e por FORMA, sem import.** `dashboard_cambio` esta sendo escrito **em paralelo** (plano 01-03, mesma onda). O `payload` recebe o cambio por parametro e so exige dois atributos (`reais_por_xm`, `informado_em`), e o teste usa um dublê congelado com a razao escrita nele. Isso mantem `dashboard_dados` puro e testavel sem disco — a conta de R$ e uma multiplicacao e nao precisa que um JSON exista para ser exercitada.
- **`Fraction(cambio.reais_por_xm)` e exato, e a multiplicacao acontece numa linha so.** `Fraction` aceita `Decimal` sem passar por `float`. E centesimos-de-XM vezes reais-por-XM da **centavos-de-R$ diretamente**, porque as duas escalas de centesimo se cancelam: dividir por 100 no meio e multiplicar por 100 no fim introduziria dois arredondamentos onde zero bastam. A derivacao esta por extenso no fonte, no molde de `formatar_taxa_derivada`.
- **`LIMIAR_DE_FRESCOR = 1 hora`, ESCOLHA e nao MEDICAO.** A coleta e de 1 Hz enquanto o `.bat` esta aberto: uma serie cuja oferta mais nova tem mais de uma hora significa que ninguem esteve na aba da Adena, e nao que o mercado parou. Ninguem mediu — nao ha serie em campo para medir — e isso esta dito.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A proibicao do `0,00` por substring reprova `30,00` — refutacao NOVA, medida aqui**

- **Found during:** Tarefa 3, portao GREEN
- **Issue:** O plano manda "um teste que percorre recursivamente todos os valores de string do payload nos cinco estados e afirma que nenhuma das frases proibidas do UI-SPEC aparece". Escrito literalmente, com `"0,00" in texto`, o teste **reprovou `"30,00 XM por milhao de adena (derivado)"`** — um valor perfeitamente legitimo, porque `0,00` e substring de `30,00`. Toda taxa terminada em zero (`10,00`, `20,00`, `30,00`) cairia junto, e a proibicao que o `01-UI-SPEC.md` escreveu nao e essa: ela e sobre `0,00` **como espaco reservado**, isto e, sobre o numero INTEIRO ser zero.
- **Fix:** `"0,00"` saiu de `FRASES_PROIBIDAS` (que ficou com as tres proibicoes que sao de fato de substring: `preço de venda`, `vendido por`, `valor de mercado`). A proibicao do zero virou uma sonda por **TOKEN** no teste — um molde `\d{1,3}(?:\.\d{3})*,\d{2}` que extrai os numeros e compara cada um por igualdade contra `"0,00"`. A refutacao, com o valor que a derrubou, esta escrita **no fonte**, ao lado de `FRASES_PROIBIDAS`, e o teste ganhou um **CONTROLE** exigindo que a sonda nova acuse um `0,00` de verdade (`"0,00 XM por milhao..."` e `"Lendo o arquivo: 0,00"`) — porque a sonda por token e mais frouxa que a de substring de proposito, e sem o controle a frouxidao poderia virar cegueira.
- **Files modified:** `l2scanner/dashboard_dados.py`, `tests/test_dashboard_dados.py`
- **Verification:** `python -m pytest tests/test_dashboard_dados.py -q` → 35 passed
- **Committed in:** `bbc2640` (commit da Tarefa 3)

**2. [Rule 3 - Blocking] A conversao do arquivo inteiro para CRLF, desfeita antes do commit**

- **Found during:** Tarefa 3, ao truncar `dashboard_dados.py` para reescrever a secao do payload
- **Issue:** O script de truncagem preservou os terminadores como os leu e devolveu o arquivo inteiro em CRLF. O blob em git e LF (`core.autocrlf=true`, sem `.gitattributes`), e o `git diff` passou a mostrar **1.626 linhas alteradas** onde havia ~580 de mudanca real — um diff impossivel de revisar e uma colisao gratuita na hora do merge com as duas irmas desta onda.
- **Fix:** O arquivo foi normalizado de volta para LF antes do `git add`; o diff caiu para **541 insercoes / 41 delecoes**, que e a mudanca de verdade. A suite foi re-executada depois da conversao (61 passed nos tres arquivos do dashboard).
- **Files modified:** `l2scanner/dashboard_dados.py` (so terminadores)
- **Verification:** `git diff --stat HEAD` antes e depois; `python -m pytest tests/test_dashboard_*.py -q` → 61 passed
- **Committed in:** `bbc2640`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Nenhum scope creep. A primeira e uma correcao de um criterio de aceitacao que estava literalmente errado, e ela produziu uma refutacao medida que agora mora no fonte — exatamente o que a doutrina da casa manda fazer com uma rota que cai. A segunda e higiene de diff. Nenhum arquivo fora dos tres de `files_modified` foi tocado, e `requirements.txt` nao ganhou uma linha.

## Issues Encountered

- **Duas execucoes da suite completa foram interrompidas pelo ambiente**, ambas parando em `tests/test_agenda.py:1231` — que e a unica linha do projeto que levanta `KeyboardInterrupt` de proposito (o `time.sleep` monkeypatchado que faz o `laco_da_agenda` dar uma volta so). **Nao e defeito**: `tests/test_agenda.py` sozinho passa (145 passed), e a execucao completa seguinte passou limpa em 165 s com **4.566 passed, 25 skipped**. Registrado aqui para o proximo nao gastar tempo perseguindo um fantasma.
- **`01-PATTERNS.md` EXISTE** e foi lido (620 linhas), ao contrario do que o `01-01-SUMMARY` reportou — ele foi commitado depois daquele plano. As secoes `A agregacao por balde de tempo` e `A montagem do JSON exibido` foram as usadas.

## User Setup Required

None — nenhuma configuracao de servico externo. Toda esta camada e pura ou somente-leitura, e a suite inteira roda em `tmp_path`.

## Next Phase Readiness

**Pronto para os planos seguintes:**
- **`payload(pasta, agora, cambio=None)` esta completo** e e o que o 01-05 vai servir em `GET /dados`. A assinatura antiga (`payload(pasta, agora)`) continua valendo — `dashboard.py` nao precisou mudar e nao mudou.
- **O 01-03 pluga direto:** basta o servidor chamar `payload(..., cambio=ler_o_cambio(pasta))`. O contrato exigido e de dois atributos, `reais_por_xm` (aceita `Decimal`) e `informado_em` (`datetime`), que e exatamente o que o `Cambio` daquele plano define. **Os dois modulos continuam sem se importar**, nos dois sentidos.
- **O 01-06/01-07 recebem o grafico pronto:** cada serie traz `pontos` (um por instante) e `baldes` nas tres larguras (`cinco_minutos`, `uma_hora`, `um_dia`), ja agregados com `median_low`. O JS **nao precisa agregar nada** — e nao deve: a disciplina do D-02 mora no Python.

**O que o proximo planejador precisa saber:**
- **A linha da mediana vai faltar na maior parte do grafico, e isso e o desenho certo** (CTX-1). Onde ela falta, `tipica_texto` traz a frase de piso do Python e `tipica_pixel` e **`None`** — nunca `0.0`. O JS tem de saber pular `null` em vez de desenhar no zero: zero e um lugar no eixo, e desenhar a ausencia la afirmaria que a taxa despencou.
- **`menor_pixel`/`tipica_pixel` sao o PIXEL; `menor_texto`/`tipica_texto` sao a VERDADE.** O tooltip e a legenda tem de sair da string. Um `toFixed()` no navegador seria o segundo formatador que o DASH-03 proibe, e ha teste no lado do Python prendendo o texto por igualdade.
- **`avisos` e uma lista de strings prontas, na ordem de exibicao.** Nenhuma delas deve ser reacentuada ou remontada no JS. As frases do estado vazio (titulo, corpo, prova) chegam ali nos tres elementos, nessa ordem.
- **`destaque` e `None` nos dois estados de falha fechada** (`erro_de_contrato`, `arquivo_ausente`), e `series` e `[]`. O JS tem de tratar isso — desenhar so a mensagem — em vez de acessar `dados.destaque.xm` direto, como o tracer ainda faz.
- **O `estado` do tracer mudou de nome.** Era `"ok"`/`"sem_evidencia"`; agora e um dos cinco de `ESTADOS`. Nenhum teste nem o `dashboard.js` dependiam dos nomes antigos, e a suite confirma.

## Self-Check: PASSED

- **Arquivos:** `l2scanner/dashboard_dados.py`, `tests/test_dashboard_leitura.py`, `tests/test_dashboard_dados.py` e este SUMMARY conferidos no disco — todos presentes.
- **Commits:** `aff569c`, `1289dff`, `cc1f86d`, `29bca76`, `f0c781c`, `bbc2640` conferidos no `git log`.
- **Suite:** `python -m pytest tests/ -q` → **4.566 passed, 25 skipped**, 0 falhas, em 165 s.
- **Criterios de aceitacao, um a um:**
  - `tests/test_dashboard_leitura.py` → **14** testes coletados (exigidos: >= 10), 0 falhas.
  - `tests/test_dashboard_dados.py` → **35** testes coletados (exigidos: >= 15), 0 falhas.
  - `pytest tests/test_dashboard_leitura.py -k "NOMEIA"` → 1 passed.
  - `grep -c "NOTA_DE_LINHA_PARCIAL" l2scanner/dashboard_dados.py` → **3** (exigido: >= 2).
  - `grep -c "13/42"` → **1**; `grep -c "69713"` → **1**; `grep -c -E "CTX-1|manteve a leitura literal"` → **1**.
  - `grep -c "1,9e-11\|1.9e-11"` → **2** (exigido: >= 1).
- **Cerca de escopo:** `git diff --stat` contra a base lista **exatamente os tres arquivos** de `files_modified`. `rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py` e `mercado_console.py` intocados; nenhum arquivo do workstream `mercado` alterado.
- **`requirements.txt`:** `git diff --stat requirements.txt` vazio — nenhuma dependencia nova.
- **`.mercado/`:** `git status --porcelain .mercado/` vazio depois da suite — nenhum teste tocou a pasta real.

## Known Stubs

Nenhum stub. Toda funcao entregue tem corpo real e teste; nao ha `TODO`, `FIXME`, `pass` de reserva, valor fabricado nem componente recebendo dado vazio. Os campos que podem vir `None` — `destaque`, `destaque.reais`, `menor_pixel`, `tipica_pixel` — sao **ausencia declarada e testada**, e nao espaco reservado: cada um tem um teste afirmando que ele e nulo no caso certo e um outro afirmando que ele nao e zero.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-01*
