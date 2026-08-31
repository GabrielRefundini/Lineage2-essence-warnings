---
phase: 04-modo-mercado-an-lise-e-console
plan: 02
subsystem: analise
tags: [estatistica, fraction, median_low, linear_regression, piso-de-evidencia, ordinal, modulo-puro, stdlib]

requires:
  - phase: 03-persist-ncia-de-observa-es
    provides: "`observacoes.csv`, o portao de contrato (`_conferir_o_terminador` / `_conferir_o_cabecalho`), as duas redes por linha (`chave_dos_campos` / `residuo_dos_campos`) e a chave de dedup SEM tempo"
  - phase: 02-leitura-de-p-gina
    provides: "`LinhaLida` com `total_em_centesimos`, `quantidade`, `chave_da_serie`, `nome_exibido` e `residuo_do_cruzamento` — os mesmos nomes de campo que o CSV herda"
provides:
  - "`l2scanner/mercado_analise.py`: modulo PURO com `unitario` (Fraction), `menor_pedido_visivel`, `mediana_dos_unitarios` (median_low), `recencia_do_preco`, `tendencia` (ordinal) e `descrever_a_tendencia`"
  - "`Evidencia`: o `n` e o piso viajando DENTRO de todo resultado, com `suficiente` e `faltam` derivados"
  - "`ObservacaoLida` e `observacoes_do_arquivo` em `mercado_registro.py`: a leitura TIPADA do CSV, pelo mesmo portao de contrato que a Fase 3 mediu"
  - "`conferir_o_terminador` e `conferir_o_cabecalho` como funcoes de MODULO — os metodos da classe passaram a delegar"
affects: [04-03-console, ANAL-01, ANAL-02, ANAL-03, ANAL-04]

actuals:
  tokens: 17051
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "`Fraction(total, quantidade)` como unico comparavel entre ofertas de quantidades diferentes — arredondamento SO na formatacao"
    - "`statistics.median_low` em vez de `median` sempre que o valor devolvido vai ser exibido como observado"
    - "Regressao com eixo `x` ORDINAL, nunca carimbo, quando os carimbos sao artefato de escrita e nao de medicao"
    - "Piso de evidencia como constante nomeada com a razao por extenso e a marca de ESCOLHA, no molde de `JANELAS_IGUAIS_PARA_CONGELAR`"
    - "Estado de evidencia insuficiente EXPLICITO no dataclass (`n`, `piso`, `faltam`, `motivo_da_ausencia`) em vez de `None` mudo"
    - "Portao de contrato extraido para funcao de modulo, com o metodo da classe delegando — uma verdade so sobre o que o arquivo e"

key-files:
  created:
    - l2scanner/mercado_analise.py
    - tests/test_mercado_analise.py
  modified:
    - l2scanner/mercado_registro.py

key-decisions:
  - "A extracao do portao de contrato foi feita como REFACTOR PURO e a prova e mecanica: `tests/test_mercado_registro.py` (1532 linhas, 80 testes) segue verde SEM uma edicao de expectativa. Os dois metodos privados viraram uma linha de delegacao cada, e os dois testes de AST da Fase 3 (`except` estreito, ausencia de `fsync`/`replace`/`now`, ausencia de `truncate`) continuam valendo sobre o modulo inteiro"
  - "`observacoes_do_arquivo` NAO deduplica, ao contrario de `_montar_o_indice`. Quem dedupa e o registro, na ESCRITA. Aqui a resposta e 'o que esta escrito no arquivo' — esconder uma linha repetida faria a contagem de evidencia da analise divergir do que o usuario ve quando abre o CSV no Sheets"
  - "Arquivo de ZERO BYTES devolve lista vazia sem escrever nada. `carregar` cria o cabecalho nesse caso porque ela e o arranque do ESCRITOR; esta e leitura pura, e a Fase 4 inteira nao reescreve o CSV"
  - "`unitario` LEVANTA `ValueError` para quantidade nao positiva, e as tres funcoes de agregacao filtram essas ofertas antes de contar o `n`. NAO ESTAVA NO PLANO: o `observacoes.csv` e um arquivo que o usuario edita a mao no Sheets (fronteira de confianca T-04-06 do proprio plano), `quantidade=0` passa em `chave_dos_campos` como inteiro valido, e `Fraction(x, 0)` derrubaria o console. Quantidade NEGATIVA e pior que um erro: ela inverteria o sinal do unitario e faria a oferta ganhar a disputa do menor pedido visivel — numero plausivel e errado, o modo de falha que a fase existe para combater. A oferta sai da conta E do `n`, porque contar como evidencia uma linha que nao entra em conta nenhuma seria inflar a evidencia"
  - "A tendencia reporta a variacao em PONTOS PERCENTUAIS (`slope * (n-1) / intercept * 100`), e nao em fracao. Medido nesta sessao sobre dez ofertas em queda monotona de 100 para 55 centesimos por unidade: o ordinal devolve -42,86%, e o eixo do carimbo devolve inclinacao de -135.104 por segundo e um percentual de -5e-7% — ele APAGA a queda inteira, e nao levanta `StatisticsError`"
  - "`intercept == 0` vira 'sem tendencia reportavel' com o motivo NOMEADO (`motivo_da_ausencia`), e nao uma divisao por zero escapando nem um `None` mudo. Totais zerados sao entrada possivel num arquivo editado a mao"
  - "O desempate do menor pedido visivel e pelo carimbo MAIS ANTIGO. Com dois anuncios de unitario identico, a resposta nao pode depender da ordem em que o arquivo foi lido"
  - "`UNIDADE_DA_JANELA = 'ofertas distintas'` e uma constante de modulo, escrita UMA vez. A palavra e o requisito: ela e o que impede o usuario de ler a reta como variacao ao longo de horas, e um teste prende que a palavra de serie temporal NAO aparece no texto"
  - "Os tres pisos (1, 5, 8) sao ESCOLHA declarada no proprio fonte, e o modulo escreve por extenso que os numeros medidos do projeto (151 paginas lidas, 189 perdidas, 39 series, piso de 7 posicoes) sao sobre a LEITURA e nao servem de substituto. A tensao com a doutrina de 'nada de constante magica' esta registrada com as duas razoes: o `calibration.json` e lido e nunca escrito por este modo, e estes numeros nao sao calibracao de pixel — sao julgamento de produto"

patterns-established:
  - "Quando duas leituras do mesmo arquivo sao necessarias, extraia o portao para funcao de modulo e faca a classe delegar — nunca escreva a segunda leitura"
  - "Todo resultado estatistico carrega o `n` e o piso DENTRO dele; quem desenha nao tem como esquecer de pedir"
  - "Quando o valor vai ser exibido como observado, a funcao de agregacao tem de devolver um valor que existiu: `median_low`, nunca `median`"
  - "Eixo `x` ordinal sempre que o carimbo for artefato de como o dado foi ESCRITO e nao de quando o fato ACONTECEU"
  - "Um numero que cai precisa dizer que caiu: o teste do eixo do carimbo roda a alternativa ERRADA e afirma que ela erra, em vez de so afirmar que a certa acerta"

requirements-completed: [ANAL-01, ANAL-03]

coverage:
  - id: D1
    description: "O `observacoes.csv` e lido em registros TIPADOS (int, int, datetime) pelo mesmo portao de contrato da Fase 3, sem um segundo parser no projeto"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAsLinhasParseadasVoltamTIPADAS::test_os_numeros_voltam_INTEIROS_e_o_carimbo_volta_DATETIME"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOPortaoDeContratoEOMESMO::test_o_ultimo_byte_cortado_deixa_seis_campos_PARSEAVEIS_e_ainda_LEVANTA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOPortaoDeContratoEOMESMO::test_cabecalho_divergente_LEVANTA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAExtracaoEREFACTOR_PURO::test_o_registro_delega_o_terminador_a_funcao_de_modulo"
        status: pass
    human_judgment: false
  - id: D2
    description: "Arquivo ausente, de zero bytes ou so com cabecalho devolve lista vazia sem levantar e sem criar nada — a `.mercado/` nasce vazia e a analise diz 'sem evidencia'"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOPortaoDeContratoEOMESMO::test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOPortaoDeContratoEOMESMO::test_a_leitura_NAO_CRIA_o_arquivo_ausente"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAExtracaoEREFACTOR_PURO::test_a_leitura_nova_NAO_abre_o_arquivo_para_escrita"
        status: pass
    human_judgment: false
  - id: D3
    description: "O comparavel entre ofertas e o unitario EXATO em `Fraction`, nunca `float`, e o total multiplicado de volta bate no centesimo"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOUnitarioEEXATO::test_o_unitario_e_Fraction_e_nao_float"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOUnitarioEEXATO::test_o_unitario_multiplicado_de_volta_devolve_o_TOTAL_exato"
        status: pass
    human_judgment: false
  - id: D4
    description: "O menor pedido visivel e a oferta de menor UNITARIO (nao de menor total), carrega os dois numeros juntos e o carimbo DAQUELA oferta"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOMenorPedidoVisivel::test_a_escolhida_e_a_de_menor_unitario_e_carrega_a_quantidade"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOMenorPedidoVisivel::test_o_MENOR_TOTAL_nao_e_o_menor_pedido_visivel"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOMenorPedidoVisivel::test_o_carimbo_e_o_DAQUELA_oferta_e_nao_o_da_serie"
        status: pass
    human_judgment: false
  - id: D5
    description: "A PROVA CENTRAL: com n=6 (par e acima do piso) a mediana devolve um valor contido na lista de entrada E diferente de `statistics.median` da mesma lista"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAMedianaDEVOLVE_VALOR_OBSERVADO::test_n_SEIS_par_e_acima_do_piso_devolve_valor_que_EXISTIU_na_tela"
        status: pass
    human_judgment: false
  - id: D6
    description: "Abaixo do piso a analise devolve o que FALTA com o piso nomeado, e nunca um numero — em n=0 para o menor, n=4 para a mediana e n=7 para a tendencia"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAMedianaDEVOLVE_VALOR_OBSERVADO::test_n_QUATRO_esta_abaixo_do_piso_e_informa_CINCO"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOMenorPedidoVisivel::test_sem_oferta_nenhuma_o_resultado_diz_o_que_FALTA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOPisoDaTendencia::test_com_SETE_ofertas_o_resultado_diz_o_que_FALTA_e_informa_OITO"
        status: pass
    human_judgment: false
  - id: D7
    description: "A recencia do PRECO e `max(primeira_vez)` do `observacoes.csv`, e a docstring nomeia o `ultima_vez` do catalogo como o fato DIFERENTE com que ela nao pode ser confundida"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAsDUAS_RECENCIAS::test_a_recencia_do_preco_e_o_MAXIMO_dos_carimbos"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAsDUAS_RECENCIAS::test_a_docstring_NOMEIA_a_outra_recencia_para_ninguem_confundir"
        status: pass
    human_judgment: false
  - id: D8
    description: "A tendencia roda sobre o ORDINAL: dez ofertas com carimbos a microssegundos e queda monotona dao variacao negativa e plausivel, enquanto o eixo do carimbo devolveria numero errado SEM levantar"
    requirement: "ANAL-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestATendenciaRodaSobreOORDINAL::test_dez_ofertas_em_queda_dao_variacao_NEGATIVA_e_PLAUSIVEL"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestATendenciaRodaSobreOORDINAL::test_o_eixo_do_CARIMBO_devolveria_numero_errado_SEM_LEVANTAR"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestATendenciaRodaSobreOORDINAL::test_a_ordem_e_por_primeira_vez_e_nao_a_do_arquivo"
        status: pass
    human_judgment: false
  - id: D9
    description: "O tamanho da janela viaja JUNTO do resultado e do texto, e a palavra que o qualifica designa ofertas distintas — nunca observacoes ao longo do tempo"
    requirement: "ANAL-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOTamanhoDaJanelaVIAJA_JUNTO::test_o_n_da_janela_e_o_numero_de_ofertas_passadas"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOTamanhoDaJanelaVIAJA_JUNTO::test_o_texto_usa_a_palavra_que_designa_OFERTAS_DISTINTAS"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOTamanhoDaJanelaVIAJA_JUNTO::test_o_texto_carrega_o_n_mesmo_ABAIXO_do_piso"
        status: pass
    human_judgment: false
  - id: D10
    description: "Nenhuma serie de entrada faz a analise levantar: lista vazia na mediana e na tendencia, unitarios todos iguais, intercepto zero e quantidade nao positiva"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestATendenciaSemQueda::test_unitarios_todos_IGUAIS_dao_variacao_ZERO"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestATendenciaSemQueda::test_intercepto_ZERO_nao_estoura_em_divisao_por_zero"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestAMedianaDEVOLVE_VALOR_OBSERVADO::test_a_mediana_de_lista_vazia_nao_LEVANTA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOUnitarioEEXATO::test_quantidade_zero_ou_negativa_LEVANTA_com_o_motivo_em_texto"
        status: pass
    human_judgment: false
  - id: D11
    description: "O modulo de analise e PURO — nao traz o modulo de sistema, nao abre arquivo, nao imprime e nao chama relogio"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOModuloDeAnaliseEPURO::test_nao_traz_o_modulo_de_sistema_nem_abre_arquivo_nem_imprime"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOModuloDeAnaliseEPURO::test_o_carimbo_nunca_vem_de_dentro"
        status: pass
      - kind: command
        ref: "python -c \"import l2scanner.mercado_analise as m, inspect; f = inspect.getsource(m); assert 'import os' not in f and 'open(' not in f and 'print(' not in f\""
        status: pass
    human_judgment: false
  - id: D12
    description: "Os tres pisos de evidencia (1, 5, 8) sao ESCOLHA declarada por escrito no fonte, com os numeros medidos do projeto nomeados como sendo sobre a LEITURA e a tensao com o `calibration.json` registrada"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOsPisosSaoESCOLHA_E_NAO_MEDICAO::test_o_modulo_DECLARA_por_escrito_que_os_pisos_sao_escolha"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOsPisosSaoESCOLHA_E_NAO_MEDICAO::test_o_fonte_diz_que_os_numeros_MEDIDOS_do_projeto_sao_sobre_a_LEITURA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_analise.py::TestOsPisosSaoESCOLHA_E_NAO_MEDICAO::test_o_fonte_explica_por_que_os_pisos_NAO_moram_no_calibration_json"
        status: pass
    human_judgment: false
  - id: D13
    description: "Os pisos 1, 5 e 8 produzem, sobre o `observacoes.csv` REAL de uma sessao de farm, um console que fala para os itens que o usuario quer ver — sem calar demais nem inventar mediana"
    requirement: "ANAL-01"
    verification: []
    human_judgment: true
    rationale: "Nenhum piso de evidencia foi medido neste projeto e o `.mercado/observacoes.csv` real ainda nao existe nesta arvore. A medicao que resolveria isso e 'quantas observacoes DISTINTAS por serie o material real produz', e ela exigiria a varredura do censo (mais de 10 minutos), deliberadamente nao rodada nesta sessao. Cada piso e uma linha; o roteiro esta no `<human-check>` do plano"

duration: 11min
completed: 2026-08-31
status: complete
---

# Phase 04 Plan 02: Analise Honesta Summary

**A metade PURA da Fase 4: unitario exato em `Fraction`, menor pedido visivel com o carimbo DELE, mediana `median_low` que so devolve valor observado, tendencia sobre o ORDINAL das ofertas distintas — e, abaixo do piso, o que FALTA em vez de um numero.**

## Performance

- **Duracao:** 11 min (03:22 a 03:33)
- **Tasks:** 3/3
- **Commits:** 6 (3 pares RED/GREEN)
- **Testes novos:** 54
- **Suite:** 2852 passed, 23 skipped (base desta arvore: 2798 passed, 23 skipped)

## O que foi construido

### Task 1 — `observacoes_do_arquivo`, pelo portao que ja existe

`RegistroDeObservacoes.carregar()` valida tudo — terminador, cabecalho, contagem de
campos, tipos — e **descarta os campos**, guardando so o `set` de chaves. A analise precisa
dos campos. A tentacao obvia seria escrever uma segunda leitura "simples" com `csv.reader`,
e ela reintroduziria exatamente o defeito que a Fase 3 gastou um plano inteiro para pegar:
das cinco truncagens medidas byte a byte, **duas produzem seis campos todos parseaveis, com
`80` virando `8`**. A contagem de campos nao pega, a validacao por tipo nao pega — so o
terminador pega.

A saida foi extrair o portao para funcoes de modulo (`conferir_o_terminador`,
`conferir_o_cabecalho`) e fazer os dois metodos privados da classe **delegarem**. Refactor
puro: `tests/test_mercado_registro.py` segue verde sem uma edicao de expectativa.

`ObservacaoLida` (frozen) carrega **exatamente** as `COLUNAS`, na ordem de `COLUNAS` — uma
coluna a mais aqui seria um dado derivado morando junto do dado afirmado, que e a objecao
que derrubou a coluna do unitario (D-02).

### Task 2 — o unitario, o menor, a mediana e as duas recencias

- **`unitario(total, quantidade) -> Fraction`.** Comparar totais entre ofertas de
  quantidades diferentes e sem sentido; o unico comparavel e o unitario, e ele e exato.
  `float` reintroduziria erro exatamente onde o parsing por molde de digito o evitou.
- **`menor_pedido_visivel`** ordena pelo unitario, carrega os dois numeros juntos e o
  carimbo **daquela oferta**. Um minimo de terca ao lado da recencia de hoje e a mentira
  plausivel que o projeto combate.
- **`mediana_dos_unitarios`** usa `median_low`. `statistics.median` de `n` par devolve a
  media dos dois do meio — meio centavo inventado, o mesmo pecado do unitario arredondado.
- **`recencia_do_preco` = `max(primeira_vez)`**, com o `ultima_vez` do catalogo nomeado na
  docstring como o outro fato, para ninguem trocar um pelo outro.

### Task 3 — a tendencia sobre o ordinal (ANAL-03)

`gravar_as_paginas` chama `relogio.agora()` **por linha**, entao as dez linhas de uma pagina
tem carimbos separados por microssegundos. **Medido nesta sessao**, sobre dez ofertas em
queda monotona de 100 para 55 centesimos por unidade:

| Eixo `x` | `slope` | Percentual sobre a janela |
|---|---|---|
| **ordinal `1..n`** | -5,0 por oferta | **-42,86%** |
| carimbo | -135.104,51 por segundo | -0,0000005% |

O eixo do carimbo **nao levanta `StatisticsError`** — tecnicamente `x` varia — e apaga a
queda inteira. Numero plausivel e errado. Ordinais sao distintos por construcao, entao o
modo de falha "x is constant" fica impossivel.

O texto sai como `tendencia: -42.9% ao longo das ultimas 10 ofertas distintas`, e um teste
prende que a palavra de serie temporal **nao** aparece.

## Resultado de cada `<automated>` do plano

| Bloco | Comando | Resultado |
|---|---|---|
| Task 1 `<verify>` | `python -m pytest tests/test_mercado_analise.py tests/test_mercado_registro.py -x -q` | **134 passed** |
| Task 2 `<verify>` #1 | `python -m pytest tests/test_mercado_analise.py -x -q` | **41 passed** |
| Task 2 `<verify>` #2 | `python -c "... assert 'import os' not in f and 'open(' not in f and 'print(' not in f ..."` | **codigo 0** |
| Task 3 `<verify>` | `python -m pytest tests/test_mercado_analise.py -x -q` | **54 passed** |
| Verificacao 1 | `python -m pytest tests/test_mercado_analise.py tests/test_mercado_registro.py -x -q` | **168 passed** |
| Verificacao 2 | `python -m pytest tests/ --ignore=tests/test_agenda.py -q` | **2852 passed, 23 skipped** |
| Verificacao 3 | pureza do modulo | **codigo 0** |
| Verificacao 4 | `test -z "$(git status --porcelain calibration.json config.toml)" \|\| ...` | **codigo 0, sem REPROVADO** |
| Verificacao 5 | `test -z "$(git diff --stat -- rastreador.py visao.py __main__.py)" \|\| ...` | **codigo 0, sem REPROVADO** |

Criterios de aceitacao por linha de comando, todos com codigo 0:

- `observacoes_do_arquivo(Path('nao-existe.csv')) == []`
- `isinstance(unitario(4000, 48), Fraction)`
- `N_MINIMO_PARA_MEDIANA == 5 and N_MINIMO_PARA_MENOR == 1`
- `'escolha' in m.__doc__.lower() or 'escolhid' in m.__doc__.lower()`
- `N_MINIMO_PARA_TENDENCIA == 8`
- `'ordinal' in inspect.getsource(m.tendencia).lower()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Funcionalidade critica ausente] Quantidade nao positiva derrubaria o console**

- **Found during:** Task 2
- **Issue:** O plano nao trata `quantidade <= 0`. O `observacoes.csv` e a fronteira de
  confianca T-04-06 do proprio plano — arquivo que o usuario **edita a mao no Sheets** —
  e `chave_dos_campos` aceita `0` como inteiro valido. `Fraction(x, 0)` levanta
  `ZeroDivisionError` e derrubaria o modo `--mercado` inteiro. Quantidade **negativa** e
  pior: nao levanta, inverte o sinal do unitario e faz a oferta ganhar a disputa do menor
  pedido visivel — numero plausivel e errado, exatamente o modo de falha que a fase existe
  para combater.
- **Fix:** `unitario` levanta `ValueError` com o motivo em texto; um helper `_comparaveis`
  tira essas ofertas da conta **e do `n`** (contar como evidencia uma linha que nao entra
  em conta nenhuma inflaria a evidencia). Nao houve mudanca em `mercado_registro.py`: a
  Fase 3 continua gravando o que a tela afirmou.
- **Files modified:** `l2scanner/mercado_analise.py`
- **Commit:** `0fc42de`

**2. [Rule 2 - Funcionalidade critica ausente] `intercept == 0` na tendencia**

- **Found during:** Task 3
- **Issue:** O plano manda tratar o caso, mas so como "caso sem tendencia reportavel". Um
  `None` cru obrigaria quem desenha a adivinhar o motivo.
- **Fix:** `Tendencia.motivo_da_ausencia` nomeia a razao (`"intercepto zero, sem base para
  percentual"` ou `"evidencia insuficiente"`), no mesmo padrao de estado explicito do resto
  do modulo.
- **Files modified:** `l2scanner/mercado_analise.py`
- **Commit:** `d3bd8d3`

### Observacoes sobre criterios do plano

**O par `(6200, 48)` e `(4500, 100)` do criterio de aceitacao NAO discrimina as duas
ordens.** `6200/48 = 129,17` e `4500/100 = 45`: a oferta de menor unitario e **tambem** a de
menor total, entao o criterio, sozinho, ficaria verde numa implementacao que ordenasse pelo
total. O criterio foi rodado **literalmente como escrito** e passa
(`test_a_escolhida_e_a_de_menor_unitario_e_carrega_a_quantidade`), e ao lado dele foi
acrescentado o par que **discrimina**: `(1000, 1)` tem o menor total e o maior unitario
(`test_o_MENOR_TOTAL_nao_e_o_menor_pedido_visivel`). Sem o segundo, a intencao do primeiro
nao estaria presa por teste nenhum.

**"Magnitude absurda" no eixo do carimbo e a INCLINACAO, nao o percentual.** O plano diz que
o eixo do carimbo "produziria magnitude absurda". Medido: a inclinacao e absurda (-135.104
por segundo), mas o **percentual sobre a janela** sai praticamente zero, porque o
`intercept` cresce junto (2,4e14). O erro e outro e e pior de detectar: em vez de gritar, o
carimbo **cala** — reporta 0% para uma serie que caiu 42,9%. O teste prende os dois fatos, e
compara com o intervalo aceitavel em vez de um numero escolhido a mao.

## Known Stubs

Nenhum. Todas as funcoes deste plano tem implementacao completa e teste que a prende. O
`ANAL-02` (destaque abaixo da mediana) e o `ANAL-04` (margem de craft) nao pertencem a este
plano e nao foram esbocados aqui — nada de `pass`, `TODO` nem retorno vazio ficou no fonte.

## Threat Flags

Nenhuma superficie nova. O plano nao instala nada, nao abre porta, nao le arquivo alem do
`observacoes.csv` (somente leitura) e nao acrescenta dependencia — `statistics`,
`fractions`, `dataclasses`, `datetime`, `csv` e `io` sao todos stdlib.

As cinco mitigacoes do `<threat_model>` estao presas por teste:

| Threat ID | Mitigacao | Teste |
|---|---|---|
| T-04-06 | portao do terminador ANTES da contagem de campos, reusado | `test_o_ultimo_byte_cortado_deixa_seis_campos_PARSEAVEIS_e_ainda_LEVANTA` |
| T-04-07 | `Fraction` como unico comparavel | `test_o_unitario_e_Fraction_e_nao_float` |
| T-04-08 | `median_low`, com `n=6` par e acima do piso | `test_n_SEIS_par_e_acima_do_piso_devolve_valor_que_EXISTIU_na_tela` |
| T-04-09 | eixo ordinal por construcao | `test_o_eixo_do_CARIMBO_devolveria_numero_errado_SEM_LEVANTAR` |
| T-04-10 | `Evidencia` viaja DENTRO do resultado | `test_o_n_da_janela_e_o_numero_de_ofertas_passadas` |

## O que o proximo plano (04-03) consome

```python
from l2scanner.mercado_analise import (
    Evidencia, MedianaDosUnitarios, MenorPedidoVisivel, Tendencia,
    descrever_a_tendencia, mediana_dos_unitarios, menor_pedido_visivel,
    recencia_do_preco, tendencia, unitario,
)
from l2scanner.mercado_registro import ObservacaoLida, observacoes_do_arquivo
```

Tres avisos para quem desenha:

1. **Agrupar por `chave_da_serie` e de quem chama.** Este modulo nao decide o que e uma
   serie — ele faz aritmetica sobre uma.
2. **Carregue o CSV UMA vez, no arranque**, e acrescente ao modelo cada observacao nova
   quando `registro.registrar(...)` devolver `True`. Reler a 1 Hz abriria corrida com o
   usuario editando o arquivo no Sheets.
3. **O destaque do ANAL-02 compara contra o modelo COMO ELE ESTA**, antes de as linhas do
   tick entrarem — senao o item se compara consigo mesmo.

## Self-Check: PASSED

Os quatro arquivos citados existem em disco (`l2scanner/mercado_analise.py`,
`l2scanner/mercado_registro.py`, `tests/test_mercado_analise.py` e este SUMMARY) e os seis
commits existem no historico: `c355c17`, `3b8bf75`, `476b433`, `0fc42de`, `53763f5`,
`d3bd8d3`.
