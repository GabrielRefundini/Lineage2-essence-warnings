---
phase: 04-modo-mercado-an-lise-e-console
plan: 03
subsystem: console
tags: [anal-01, anal-02, anal-03, watchlist, destaque, evidencia, texto-puro, zero-install, ast]

requires:
  - phase: 04-modo-mercado-an-lise-e-console
    provides: "04-01: `laco_do_mercado`, `mercado_console` com `linha_ao_vivo`/`resumo_da_sessao`, e os tres fios ligados no tick"
  - phase: 04-modo-mercado-an-lise-e-console
    provides: "04-02: `mercado_analise` puro (`unitario`, `menor_pedido_visivel`, `mediana_dos_unitarios`, `recencia_do_preco`, `tendencia`, `Evidencia`) e `observacoes_do_arquivo`"
provides:
  - "`ler_watchlist_do_mercado` no FIM de `l2scanner/config.py`: a watchlist lida sem arrastar DPI nem `cv2` de GUI"
  - "`ModeloDeMercado` em `mercado_analise.py`: a historia agrupada por serie, carregada UMA vez e crescida por `acrescentar`"
  - "`Destaque` + `ModeloDeMercado.veredito_do_destaque`: ANAL-02 contra a mediana de ANTES do tick, com tres estados explicitos"
  - "`ordenar_para_o_console` + `SerieNoConsole`: a watchlist como filtro de DESTAQUE, e o topo por evidencia quando ela nao existe"
  - "`secao_do_vale_quanto`, `destaque_ao_vivo`, `formatar_centesimos` e `formatar_unitario_derivado` em `mercado_console.py`"
  - "`tests/test_mercado_console.py`: a tupla `EXPRESSOES_PROIBIDAS` varrendo o texto DEVOLVIDO e o FONTE de dois modulos"
affects: [04-04, 04-05, ANAL-01, ANAL-02, ANAL-03]

actuals:
  tokens: 19280
  tasks: 3
  commits: 7

tech-stack:
  added: []
  patterns:
    - "Duas leituras da MESMA chave de TOML quando os dois chamadores tem custos de import diferentes, com a duplicacao declarada por escrito em vez de escondida"
    - "Estado derivado exposto por metodo do modelo (`contagem_de`, `nome_exibido_de`) em vez de o console alcancar o dicionario interno"
    - "Assercao sobre A LINHA (`linha_com`) e nao sobre o texto inteiro, quando o criterio e 'este numero esta NESTE rotulo'"
    - "Varredura de nomenclatura em DUAS camadas: o texto DEVOLVIDO e o `inspect.getsource` do modulo, porque a primeira nao alcanca rotulo de outra funcao, comentario nem docstring"
    - "Prova sobre o CODIGO EXECUTAVEL (docstrings arrancadas pelo AST, comentarios sumidos no `ast.unparse`) quando um criterio de substring reprovaria a documentacao"
    - "Secao de console que sai no ARRANQUE e por INTERVALO, nunca por tick, quando a resposta que ela da so muda por evento"

key-files:
  created:
    - tests/test_mercado_console.py
  modified:
    - l2scanner/config.py
    - l2scanner/mercado_analise.py
    - l2scanner/mercado_console.py
    - l2scanner/mercado_modo.py
    - tests/test_mercado_modo.py

key-decisions:
  - "A ordem do tick e a de quatro passos NUMERADOS no fonte — julgar, catalogo, registro, e so entao `acrescentar` — e a razao esta escrita ALI, junto do passo 1, e nao so no teste. O teste que a prende foi montado para DISCRIMINAR: cinco ofertas de unitarios 100..140 dao `median_low` = 120, e a sexta muito barata levaria a mediana de seis para 110. O teste afirma PRIMEIRO que os dois numeros diferem, e so entao que a referencia usada foi 120 — sem essa primeira assercao o cenario poderia ficar verde sobre a implementacao errada"
  - "`SERIES_NO_TOPO = 8` corta o RABO por evidencia e NUNCA a watchlist: um item marcado que sumisse por corte seria a watchlist virando porta de SAIDA, que e o defeito simetrico ao que a Fase 2 corrigiu na porta de entrada. Ha teste com `SERIES_NO_TOPO + 5` series ricas mais uma serie de `n=1` marcada, afirmando que ela e a primeira e que o total devolvido e `SERIES_NO_TOPO + 1`"
  - "O casamento watchlist-serie e EXATO sobre `casefold` + espacos colapsados, e a recusa do fuzzy esta escrita no fonte. O `CLAUDE.md` recomenda `rapidfuzz` para nome de membro de party, e para AQUELE problema ele esta certo; aqui seria um defeito, porque `+3 Dragon Belt` e `+4 Dragon Belt` diferem em UM caractere e sao series deliberadamente separadas — medido, o mesmo nome base valia de 7,02 a 100,00 conforme o encanto"
  - "A recencia sai em DUAS formas na mesma linha, e a linha do menor pedido visivel carrega o carimbo DAQUELA oferta enquanto a linha da mediana carrega o `max(primeira_vez)` da serie. O teste monta o cenario para os dois DIFERIREM (10:00 contra 18:00) e afirma sobre A LINHA, nao sobre o texto: `'10:00' in texto` ficaria verde com o carimbo certo aparecendo em qualquer outro lugar do bloco"
  - "`config.toml` quebrado NAO derruba a coleta. NAO ESTAVA NO PLANO: `ler_watchlist_do_mercado` LEVANTA de proposito para TOML invalido (T-04-11), porque do lado de quem edita o arquivo a recusa alta e o certo — mas deixar esse `raise` escapar dentro do laco mataria o modo `--mercado` inteiro por causa de uma virgula, e o que o usuario perderia seria a COLETA da noite. A watchlist e filtro de DESTAQUE, nao o produto"
  - "CSV de historico ilegivel tambem degrada a ANALISE e nao o modo, pela mesma assimetria: o produto do modo e COLETAR, e a analise e uma leitura do que ja foi coletado. As duas mensagens seguem o padrao da casa (o que quebrou, o que continua funcionando)"
  - "Quantidade nao positiva na linha lida agora sai SEM_DESTAQUE em vez de levantar. A grade e leitura de TELA: `quantidade=0` e leitura possivel, e um `ZeroDivisionError` derrubaria o modo no meio do farm por uma celula mal lida. Empate com a mediana tambem nao e destaque, porque o ANAL-02 promete 'abaixo' e um empate nao esta abaixo de nada"
  - "A secao repinta por INTERVALO (`SEGUNDOS_ENTRE_SECOES = 60`, ESCOLHA declarada) e sai ja no ARRANQUE, antes do primeiro tick — o usuario abre o programa para perguntar 'vale quanto agora?' e a resposta ja existe no disco da sessao passada. O teste afirma EXATAMENTE uma secao em seis ticks; um `>= 1` ficaria verde tambem com seis"
  - "O `residuo_do_cruzamento` continua fora do repintar, e ha teste afirmando isso. A guarda de cruzamento esta DESLIGADA por medicao: o residuo e observacao e nao veredito, e ja esta em coluna propria no CSV"

patterns-established:
  - "Quando o criterio e 'este numero esta NESTE rotulo', afirme sobre a LINHA extraida e nao sobre o texto inteiro — e faca o helper falhar se houver zero ou mais de uma linha com a marca"
  - "Um teste de nomenclatura precisa de duas camadas: o texto devolvido pega o rotulo, o `inspect.getsource` pega o comentario, a docstring e a funcao vizinha que nenhum outro teste varre"
  - "Quando um criterio de substring reprovaria a propria documentacao, rode-o como escrito, reporte, e acrescente ao lado a prova sobre o CODIGO com a prosa arrancada pelo AST — mais forte, e nao mais fraca"
  - "Toda funcao de excecao de config que o laco de producao chama precisa de um `except` nomeado no laco: a recusa alta e certa para quem edita o arquivo e errada para quem esta farmando ha tres horas"

requirements-completed: [ANAL-01, ANAL-02, ANAL-03]

coverage:
  - id: D1
    description: "A watchlist e lida do `config.toml` sem arrastar DPI nem `cv2` de GUI, e ausencia de arquivo, de secao ou de chave devolve lista vazia sem levantar"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_secao_presente_SEM_A_CHAVE_devolve_lista_vazia"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_o_config_NAO_IMPORTA_a_ferramenta_de_calibracao"
        status: pass
    human_judgment: false
  - id: D2
    description: "T-04-11: tipo errado na watchlist e recusa de arranque nomeando o arquivo, a posicao do item ruim e o formato certo"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_a_chave_como_TEXTO_SOLTO_e_recusada_com_o_formato_certo"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_item_NAO_TEXTO_dentro_da_lista_e_recusado_nomeando_a_posicao"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestALeituraDaWatchlist::test_TOML_QUEBRADO_e_erro_de_arranque_e_nomeia_o_arquivo"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sem watchlist o console responde para as series com MAIS EVIDENCIA; com watchlist as dela vem primeiro e MARCADAS e o resto continua visivel abaixo"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAOrdenacaoParaOConsole::test_SEM_watchlist_as_series_com_MAIS_EVIDENCIA_vem_primeiro"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAOrdenacaoParaOConsole::test_COM_watchlist_a_dela_vem_PRIMEIRA_e_MARCADA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAOrdenacaoParaOConsole::test_o_TOPO_e_limitado_mas_a_watchlist_NUNCA_e_cortada"
        status: pass
    human_judgment: false
  - id: D4
    description: "O casamento e exato sobre caixa normalizada e nunca fuzzy: variante de encanto nao casa"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAOrdenacaoParaOConsole::test_o_casamento_normaliza_caixa_e_colapsa_espacos"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAOrdenacaoParaOConsole::test_o_casamento_NAO_e_fuzzy_e_variante_de_encanto_nao_casa"
        status: pass
    human_judgment: false
  - id: D5
    description: "O CSV e lido UMA vez, no arranque, e o modelo conhece as series dele antes do primeiro tick"
    requirement: "ANAL-01"
    verification:
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestOModeloCarregaUmaVezESoCresce::test_o_modelo_conhece_o_CSV_PRE_EXISTENTE_antes_do_primeiro_tick"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestOModeloCarregaUmaVezESoCresce::test_o_arquivo_de_observacoes_e_lido_UMA_VEZ_em_varios_ticks"
        status: pass
    human_judgment: false
  - id: D6
    description: "A PROVA CENTRAL (T-04-12): o destaque e calculado contra a mediana de ANTES do tick, e o cenario afirma primeiro que as duas medianas DIFEREM"
    requirement: "ANAL-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestODestaqueEContraAHistoriaDeANTES::test_a_referencia_e_a_mediana_de_ANTES_e_nao_a_de_DEPOIS"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestODestaqueEContraAHistoriaDeANTES::test_abaixo_da_mediana_e_DESTAQUE_e_acima_NAO_E"
        status: pass
      - kind: command
        ref: "python -c \"import inspect, l2scanner.mercado_modo as m; assert 'ANTES' in inspect.getsource(m)\""
        status: pass
    human_judgment: false
  - id: D7
    description: "Abaixo do piso da mediana nao ha destaque nenhum, nem positivo nem negativo, e a duplicada nao entra duas vezes no modelo"
    requirement: "ANAL-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestODestaqueEContraAHistoriaDeANTES::test_ABAIXO_DO_PISO_o_veredito_e_SEM_DESTAQUE_e_nao_abaixo_nem_acima"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestOModeloCarregaUmaVezESoCresce::test_a_MESMA_linha_duas_vezes_sobe_a_contagem_do_modelo_em_UM"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestODestaqueEContraAHistoriaDeANTES::test_quantidade_NAO_POSITIVA_na_linha_nova_nao_derruba_o_veredito"
        status: pass
    human_judgment: false
  - id: D8
    description: "T-04-16: a expressao de transacao proibida nao aparece no texto devolvido NEM no fonte de `mercado_console` e `mercado_modo`, item por item da tupla"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestANomenclaturaEstaPresa::test_nenhuma_EXPRESSAO_PROIBIDA_no_texto_devolvido"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestANomenclaturaEstaPresa::test_nenhuma_EXPRESSAO_PROIBIDA_no_FONTE_dos_dois_modulos"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestANomenclaturaEstaPresa::test_o_rotulo_do_requisito_ESTA_no_texto"
        status: pass
    human_judgment: false
  - id: D9
    description: "T-04-13: todo numero sai com `n` e carimbo, o total nunca sem a quantidade ao lado, e o unitario marcado como derivado"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAEvidenciaViajaColadaAoNumero::test_o_n_e_o_TOTAL_com_a_QUANTIDADE_ao_lado"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAEvidenciaViajaColadaAoNumero::test_o_unitario_aparece_MARCADO_COMO_DERIVADO"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAEvidenciaViajaColadaAoNumero::test_a_recencia_sai_nas_DUAS_formas_relativa_e_absoluta"
        status: pass
    human_judgment: false
  - id: D10
    description: "T-04-14: a linha do menor pedido visivel carrega o carimbo DAQUELA oferta, e o console nao USA o `ultima_vez` do catalogo"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAEvidenciaViajaColadaAoNumero::test_o_carimbo_do_menor_e_o_DAQUELA_OFERTA_e_nao_o_da_serie"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestASecaoNaoQuebraEMarcaAWatchlist::test_o_console_NAO_USA_o_ultima_vez_do_catalogo"
        status: pass
    human_judgment: false
  - id: D11
    description: "Abaixo do piso o texto diz o que FALTA (contagem atual e piso) e nao imprime mediana nenhuma"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAbaixoDoPisoOTextoDIZ_O_QUE_FALTA::test_serie_de_TRES_informa_a_contagem_e_o_PISO_sem_imprimir_mediana"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAbaixoDoPisoOTextoDIZ_O_QUE_FALTA::test_com_menos_que_o_piso_da_tendencia_o_texto_diz_o_que_falta"
        status: pass
    human_judgment: false
  - id: D12
    description: "A tendencia sai com o tamanho da janela junto, em ofertas distintas"
    requirement: "ANAL-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestAbaixoDoPisoOTextoDIZ_O_QUE_FALTA::test_a_tendencia_carrega_o_TAMANHO_DA_JANELA"
        status: pass
    human_judgment: false
  - id: D13
    description: "T-04-15: sem ancora no relogio o cabecalho avisa EXATAMENTE uma vez, e com ancora nao avisa nada"
    requirement: "ANAL-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_console.py::TestOAvisoDoRelogioSaiUMA_VEZ::test_relogio_SEM_ANCORA_avisa_exatamente_uma_vez"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_console.py::TestOAvisoDoRelogioSaiUMA_VEZ::test_relogio_ANCORADO_nao_avisa_nada"
        status: pass
    human_judgment: false
  - id: D14
    description: "A secao sai no arranque e por intervalo, nunca por tick; e nem `config.toml` quebrado nem CSV ilegivel derrubam a COLETA"
    requirement: "ANAL-01"
    verification:
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestACadenciaDaSecaoDeAnalise::test_a_secao_sai_no_ARRANQUE_e_NAO_uma_vez_por_tick"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestACadenciaDaSecaoDeAnalise::test_config_toml_QUEBRADO_nao_derruba_a_COLETA"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestACadenciaDaSecaoDeAnalise::test_a_watchlist_e_LIDA_DO_CONFIG_quando_ninguem_injeta"
        status: pass
    human_judgment: false
  - id: D15
    description: "Sobre um `observacoes.csv` REAL de farm, a secao responde para os itens que o usuario reconhece, o destaque aparece na hora em que ele ve a linha barata na tela, e a divergencia com a letra do criterio 3 do ROADMAP e aceitavel para ele"
    requirement: "ANAL-02"
    verification: []
    human_judgment: true
    rationale: "Tres coisas so o campo fecha. (1) `SERIES_NO_TOPO = 8` e o `SEGUNDOS_ENTRE_SECOES = 60` sao ESCOLHA e nao medicao — se o console calar demais ou repintar de menos, cada um e uma linha. (2) O destaque so aparece acima do piso da mediana (5 ofertas distintas por serie), e quantas series reais atingem esse piso numa sessao nao foi medido: a medicao exigiria a varredura do censo, deliberadamente nao rodada. (3) A DIVERGENCIA DELIBERADA: o criterio 3 diz 'para cada item da watchlist', e esta fase responde para os itens com mais evidencia quando nao ha watchlist. A decisao esta travada no `04-CONTEXT.md` e foi tomada por Claude, nao pelo usuario — ela esta aqui em voz alta exatamente para ele poder discordar"

duration: 34min
completed: 2026-08-31
status: complete
---

# Phase 04 Plan 03: "Vale quanto agora?" Summary

**A juncao: a watchlist volta como FILTRO DE DESTAQUE e nunca como porta de entrada, o modelo carrega UMA vez e cresce por observacao aceita, e a linha lida agora e julgada contra a mediana de ANTES dela — com `n`, carimbo e tamanho de janela colados em todo numero que sai na tela.**

## Performance

- **Duracao:** 34 min
- **Tasks:** 3/3
- **Commits:** 7 (3 pares RED/GREEN + 1 teste de correcao de criterio)
- **Testes novos:** 45 (34 em `test_mercado_console.py`, 11 em `test_mercado_modo.py`)
- **Suite:** 2951 passed, 23 skipped (base desta arvore, medida antes de tocar nada: **2905 passed, 23 skipped**)

> A base desta arvore nao e o "2926 passed, 2 skipped" da arvore principal, e a
> diferenca nao e regressao: este worktree esta em `18d0c71` (onda 1 mesclada) e nao
> carrega o trabalho em curso do agente de `tiat`/`identidade`. O que importa e o
> delta desta execucao: **+46 passed, skips inalterados, zero falhas novas.**

## O que foi construido

### Task 1 — a watchlist como DESTAQUE, e o topo por evidencia quando ela nao existe

`ler_watchlist_do_mercado` entrou no **FIM** de `config.py`, sem tocar uma linha do
que ja estava la, no molde literal de `ler_bosses`: arquivo ausente nao e erro, secao
ausente nao e erro, TOML quebrado E erro de arranque. As duas recusas sao os dois
erros que o usuario consegue escrever — a chave como texto solto (que iteraria os
CARACTERES: `D`, `r`, `a`, `g`...) e um item nao-texto dentro da lista, com a
**posicao** nomeada.

**Ela nao importa a ferramenta de calibracao**, e a razao esta escrita no fonte:
aquele modulo chama `tornar_consciente_de_dpi()` no proprio import e traz `cv2`
junto. Reusar `calibrar_mercado.ler_watchlist` seria pagar DPI, OpenCV e janela de
GUI por uma leitura de TOML dentro do laco de producao.

`ordenar_para_o_console` implementa a decisao travada, e a **divergencia com a letra
do criterio 3 do ROADMAP esta escrita na docstring** — sem watchlist, as series com
mais evidencia primeiro; com watchlist, as dela primeiro e MARCADAS, e o resto
continua visivel abaixo. `SERIES_NO_TOPO = 8` corta o rabo por evidencia e **nunca a
watchlist**.

### Task 2 — o modelo no laco, e a ordem que e o coracao do ANAL-02

A carga e **unica**, no arranque, via `mercado_registro.observacoes_do_arquivo` —
chamada **pelo modulo** e nao por nome importado, que e o que permite ao teste
envolver a funcao num contador e AFIRMAR "uma vez" em vez de confiar na leitura do
fonte.

A ordem do tick esta fixada em quatro passos numerados no proprio laco:

| Passo | O que | Por que nessa posicao |
|---|---|---|
| 1 | `modelo.veredito_do_destaque(linha)` | Contra o modelo COMO ELE ESTA. Se as linhas do tick ja tiverem entrado, o item se compara CONSIGO MESMO |
| 2 | `catalogo.registrar` | A Fase 3 le a chave que a Fase 2 produziu |
| 3 | `registro.registrar` | O `True` e o unico sinal de "nao era duplicada e o registro esta ligado" |
| 4 | `modelo.acrescentar` | **So** quando o passo 3 devolveu `True` |

A observacao montada no passo 4 e **campo a campo a mesma** que
`campos_da_observacao` acabou de escrever no CSV, com o **mesmo** `agora`: a historia
em memoria e o arquivo concordam por construcao, e nao por coincidencia.

### Task 3 — o desenho, com a evidencia colada ao numero

Tres linhas por serie, texto puro, sem dependencia nova:

```
**********************************************************
  VALE QUANTO AGORA?                               [18:02]
**********************************************************

  Item Raro [watchlist]
    menor pedido visivel: 7,00 por 1 unidade = 7,00 por unidade (derivado) | n=3 | ha 1 h (31/08 17:00)
    mediana: sem evidencia - 3 de 5 ofertas distintas, faltam 2
    tendencia: evidencia insuficiente com 3 ofertas distintas (preciso de 8)

  Dragon Belt
    menor pedido visivel: 45,00 por 100 unidades = 0,45 por unidade (derivado) | n=12 | ha 8 h (31/08 10:00)
    mediana: 9.040,00 por unidade (derivado) | n=12 | oferta mais nova ha 2 min (31/08 18:00)
    tendencia: +65.4% ao longo das ultimas 12 ofertas distintas
```

Note as **duas recencias na mesma tela e em linhas diferentes**: `10:00` na linha do
menor (o carimbo DAQUELA oferta) e `18:00` na linha da mediana (o
`max(primeira_vez)` da serie). Sao dois fatos distintos, e o teste monta o cenario
justamente para eles diferirem.

A tendencia **delega a `descrever_a_tendencia`** do 04-02 em vez de montar a frase
aqui: montar a segunda frase de tendencia do projeto seria criar a que um dia
esqueceria o `n`.

## Resultado de CADA `<automated>` do plano

| Bloco | Comando | Resultado |
|---|---|---|
| Task 1 `<verify>` #1 | `python -m pytest tests/test_mercado_console.py -x -q` | **33 passed** (34 apos o commit de correcao de criterio) |
| Task 1 `<verify>` #2 | `python -m pytest tests/test_mira_da_janela.py tests/test_relogio_no_laco.py -x -q` | **38 passed** |
| Task 2 `<verify>` | `python -m pytest tests/test_mercado_modo.py tests/test_mercado_analise.py -x -q` | **104 passed** |
| Task 3 `<verify>` | `python -m pytest tests/test_mercado_console.py tests/test_mercado_modo.py -x -q` | **83 passed** |
| Verificacao 1 | `python -m pytest tests/test_mercado_console.py tests/test_mercado_modo.py tests/test_mercado_analise.py -x -q` | **137 passed** (138 apos a correcao) |
| Verificacao 2 | `python -m pytest tests/ --ignore=tests/test_agenda.py -q` | **2951 passed, 23 skipped** (base 2905/23) |
| Verificacao 3 | `test -z "$(git diff --stat -- rastreador.py visao.py __main__.py config.toml)" \|\| ...` | **EXIT 0, sem REPROVADO** |
| Verificacao 4 | `test -z "$(git status --porcelain calibration.json)" \|\| ...` | **EXIT 0, sem REPROVADO** |
| Verificacao 5 | `test -z "$(git diff -- requirements.txt)" \|\| ...` | **EXIT 0, sem REPROVADO** |

**As tres guardas foram testadas contra um CONTROLE NEGATIVO**, porque uma guarda que
nunca reprova nao discrimina: sujei `l2scanner/__main__.py` de proposito, a
Verificacao 3 saiu com **EXIT 1 e a mensagem `REPROVADO`**, e o arquivo foi
restaurado com `git checkout --` (confirmado limpo por `git status --porcelain`).

### Criterios de aceitacao por linha de comando

| Criterio | Resultado |
|---|---|
| `ler_watchlist_do_mercado(Path('nao-existe.toml')) == []` | **EXIT 0** |
| `'criterio 3' in getsource(ordenar_para_o_console) or 'ROADMAP' in ...` | **EXIT 0** |
| `'ANTES' in getsource(l2scanner.mercado_modo)` | **EXIT 0** |
| `'calibrar_mercado' not in getsource(l2scanner.config)` | **REPROVA — ver abaixo** |
| `grep -n "ultima_vez" l2scanner/mercado_console.py` sem ocorrencia | **REPROVA — ver abaixo** |

Os demais criterios de aceitacao das tres tasks sao assercoes de teste e estao na
tabela `coverage` do frontmatter, todos `pass`.

## Dois criterios que REPROVAM, rodados como escritos e reportados

Os dois foram rodados **literalmente**, os dois reprovam, e em nenhum dos dois a
causa e o trabalho deste plano. Em vez de trocar o criterio calado, cada um ganhou
ao lado a prova que **discrimina**.

### 1. `'calibrar_mercado' not in inspect.getsource(l2scanner.config)`

**Ele ja reprovava na arvore PRISTINA, antes de eu tocar em nada.** Provado
mecanicamente:

```
$ git show 9dcccbf:l2scanner/config.py | grep -n "calibrar_mercado"
791:    # `calibrar_mercado.ler_watchlist` faz para `watchlist` string.
```

E a **unica** ocorrencia no arquivo, hoje e em `9dcccbf`: um comentario de
`_personagem_do_arquivo` que aponta o precedente da recusa de tipo. A restricao 3 do
proprio plano manda "a funcao nova vai no FIM do modulo, **sem tocar nada
existente**" — satisfazer o criterio exigiria editar aquele comentario, ou seja,
violar a restricao para satisfazer o criterio. A funcao nova que escrevi contribui
**zero** ocorrencias: onde ela precisa citar a ferramenta, ela escreve "a ferramenta
de calibracao".

**O que discrimina** (o que o criterio queria dizer): *config nao ARRASTA a
ferramenta*. A prova esta em
`TestALeituraDaWatchlist::test_o_config_NAO_IMPORTA_a_ferramenta_de_calibracao`, que
le os imports do **AST** — inclusive os adiados dentro de funcao, que uma varredura
de substring nao alcanca — e afirma que nenhum deles cita `calibrar_mercado`. **EXIT
0.**

### 2. `grep -n "ultima_vez" l2scanner/mercado_console.py` sem ocorrencia

A unica ocorrencia esta na **docstring** de `_linha_da_mediana`, onde nomeio a OUTRA
recencia para ninguem trocar as duas. Esse criterio e **insatisfazivel junto com uma
decisao que o plano 04-02 ja travou POR TESTE**:

```
tests/test_mercado_analise.py:451
    def test_a_docstring_NOMEIA_a_outra_recencia_para_ninguem_confundir(self):
        doc = analise.recencia_do_preco.__doc__ or ""
        assert "ultima_vez" in doc
```

Ali a prosa e **obrigada** a citar `ultima_vez`, exatamente para prevenir a confusao
que o T-04-14 descreve. Apagar a mesma prosa deste modulo para satisfazer o grep
tiraria o aviso do lugar onde ele protege, e deixaria o proximo leitor sem saber que
existem duas recencias.

**O que discrimina:** `TestASecaoNaoQuebraEMarcaAWatchlist::test_o_console_NAO_USA_o_ultima_vez_do_catalogo`
arranca docstrings pelo AST (e comentarios, que o `ast.unparse` nao reemite) e afirma
sobre o **codigo executavel**. E a mesma tecnica que
`tests/test_mercado_firewall_de_fase.py` ja estabeleceu nesta arvore para esta classe
de problema. O teste tambem afirma que a mencao em **prosa continua la** — senao
ficaria verde tambem com o aviso apagado.

**Controle negativo do proprio teste**, medido nesta sessao:

| Fonte | `ultima_vez` no codigo com prosa arrancada |
|---|---|
| so cita na docstring, usa `primeira_vez` | `False` (aprova, correto) |
| cita na docstring **e usa** `x.ultima_vez` | `True` (reprova, correto) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Funcionalidade critica ausente] `config.toml` quebrado mataria o modo `--mercado` inteiro**

- **Found during:** Task 3
- **Issue:** `ler_watchlist_do_mercado` LEVANTA `AgendaInvalida` para TOML invalido e
  para tipo errado — e isso e correto, e o proprio T-04-11 pede. Mas o plano manda o
  laco chama-la, e nao diz nada sobre capturar. Um `raise` escapando ali derrubaria o
  modo de coleta inteiro por causa de uma virgula no `config.toml`, e o que o usuario
  perderia seria a **coleta da noite** — por causa de um filtro de destaque que ele
  nunca preencheu.
- **Fix:** `except AgendaInvalida` nomeado no laco, com as DUAS mensagens do padrao da
  casa (o que quebrou, o que continua funcionando) e `watchlist = []`. Teste
  `test_config_toml_QUEBRADO_nao_derruba_a_COLETA` afirma codigo de saida `0` e a
  presenca da segunda mensagem.
- **Files modified:** `l2scanner/mercado_modo.py`, `tests/test_mercado_modo.py`
- **Commit:** `374fd72`

**2. [Rule 2 - Funcionalidade critica ausente] CSV de historico ilegivel derrubaria a coleta pela vista**

- **Found during:** Task 2
- **Issue:** `observacoes_do_arquivo` levanta `ContratoDoArquivoQuebrado` e `OSError`.
  Se `montar_registro_de_mercado` passou, o arquivo passou — mas o `.mercado/` e uma
  pasta que o **usuario abre no Sheets**, e entre as duas leituras ha uma janela real
  de corrida.
- **Fix:** `except` estreito e nomeado, degradando a **analise** para modelo vazio e
  mantendo a **coleta** de pe, com as duas mensagens do padrao da casa. A assimetria
  com os portoes de arranque (que RECUSAM a subir) esta escrita no comentario: la a
  feature e o produto, aqui ela e a vista sobre o que ja foi coletado.
- **Files modified:** `l2scanner/mercado_modo.py`
- **Commit:** `842f0de`

**3. [Rule 1 - Bug] `quantidade` nao positiva na linha lida agora derrubaria o veredito**

- **Found during:** Task 2
- **Issue:** `unitario` levanta `ValueError` para quantidade nao positiva (decisao do
  04-02). O plano nao trata o caso do lado do destaque. A grade e leitura de **tela** —
  `quantidade=0` e leitura possivel — e o `ValueError` escapando de
  `veredito_do_destaque` derrubaria o modo no meio do farm por uma celula mal lida.
- **Fix:** `except ValueError` devolvendo `SEM_DESTAQUE`. Teste
  `test_quantidade_NAO_POSITIVA_na_linha_nova_nao_derruba_o_veredito`.
- **Files modified:** `l2scanner/mercado_analise.py`
- **Commit:** `842f0de`

### Divergencias de estrutura, ditas em voz alta

**`ModeloDeMercado` nasceu na Task 1 e nao na Task 2.** O plano lista
`ordenar_para_o_console(modelo, watchlist)` na Task 1 e `ModeloDeMercado` na Task 2 —
mas a primeira **recebe** a segunda, e nao ha como escrever o teste vermelho da Task 1
sem o tipo existir. A saida foi criar na Task 1 o **container puro** (agrupamento,
`series`, `contagem_de`, `nome_exibido_de`, `observacoes_de`) e a Task 2 acrescentar o
que e dela: `acrescentar`, `Destaque` e `veredito_do_destaque`. A alternativa —
testar a Task 1 contra um dicionario falso — teria prendido a ordenacao a um dublê e
nao ao objeto real.

**`destaque_ao_vivo` (item **(g)** da Task 3) foi escrita na Task 2**, em
`mercado_console.py`, que a Task 2 nao lista em `<files>`. A alternativa era a Task 2
computar o veredito e **nao usa-lo**, deixando um valor morto no commit — ou montar o
texto dentro de `mercado_modo.py`, violando a disciplina "quem desenha e o console,
quem imprime e o laco" que o 04-01 estabeleceu. Escrever a funcao de desenho no modulo
de desenho, um commit antes, foi a opcao que nao cria divida nem quebra o padrao.

**A `<verify>` da Task 1 nomeia `tests/test_mira_da_janela.py` e
`tests/test_relogio_no_laco.py`**, que nao tem relacao com a watchlist. Foram rodados
como escritos (38 passed) e a suite inteira tambem.

### Observacao sobre um criterio que quase nao discriminava

O criterio da Task 3 *"um teste com serie de `n=3` afirma que o texto informa a
contagem `3` e o piso `5`, e que nenhum valor de mediana foi impresso"* — a segunda
metade e uma assercao **negativa**, e uma assercao negativa mal montada aprova
qualquer coisa. O teste foi escrito com uma serie cujos unitarios sao `7,00`, `8,00` e
`9,00`: `median_low` devolveria **exatamente `8,00`**, que nao aparece em nenhuma
outra linha da secao (o menor mostra `7,00`). O `assert "8,00" not in texto` so passa
se a mediana realmente nao foi impressa.

Do mesmo modo, `linha_com()` — o helper que extrai **a** linha com uma marca — falha
quando ha **zero ou mais de uma**. Um `assert "10:00" in texto` ficaria verde com o
carimbo certo aparecendo em qualquer outro lugar do bloco, que e precisamente o engano
que o criterio da recencia existe para pegar.

## Known Stubs

Nenhum. Toda funcao deste plano tem implementacao completa e teste que a prende.
Nenhum `pass`, `TODO`, `FIXME` nem retorno vazio ficou no fonte. O `ANAL-04` (margem
de craft) nao pertence a este plano e nao foi esbocado aqui.

## Threat Flags

Nenhuma superficie nova. O plano nao instala nada, nao abre porta, nao envia rede e
nao acrescenta dependencia — `ast`, `tomllib`, `fractions`, `datetime`, `statistics` e
`dataclasses` sao todos stdlib. `requirements.txt` esta byte-identico (Verificacao 5,
EXIT 0). O `rich` continua fora, por doutrina de zero-install.

**A analise LE o CSV e NUNCA o reescreve** — `observacoes_do_arquivo` abre so em
modo leitura, e o teste do 04-02
(`test_a_leitura_nova_NAO_abre_o_arquivo_para_escrita`) continua verde.

As seis mitigacoes do `<threat_model>` estao presas por teste:

| Threat ID | Mitigacao | Teste |
|---|---|---|
| T-04-11 | recusa de arranque nomeando arquivo, posicao e formato | `test_a_chave_como_TEXTO_SOLTO_e_recusada_com_o_formato_certo`, `test_item_NAO_TEXTO_dentro_da_lista_e_recusado_nomeando_a_posicao` |
| T-04-12 | ordem do tick fixada e comentada | `test_a_referencia_e_a_mediana_de_ANTES_e_nao_a_de_DEPOIS` |
| T-04-13 | `n` e carimbo em toda linha, total nunca sem quantidade | `test_o_n_e_o_TOTAL_com_a_QUANTIDADE_ao_lado`, `test_serie_de_TRES_informa_a_contagem_e_o_PISO_sem_imprimir_mediana` |
| T-04-14 | carimbo DAQUELA oferta; `ultima_vez` fora do codigo | `test_o_carimbo_do_menor_e_o_DAQUELA_OFERTA_e_nao_o_da_serie`, `test_o_console_NAO_USA_o_ultima_vez_do_catalogo` |
| T-04-15 | aviso unico quando o relogio nao tem ancora | `test_relogio_SEM_ANCORA_avisa_exatamente_uma_vez` |
| T-04-16 | `EXPRESSOES_PROIBIDAS` sobre o texto **e** sobre o FONTE | `test_nenhuma_EXPRESSAO_PROIBIDA_no_texto_devolvido`, `test_nenhuma_EXPRESSAO_PROIBIDA_no_FONTE_dos_dois_modulos` |

## Restricoes da fase, conferidas

| Restricao | Estado |
|---|---|
| Nao tocar `rastreador.py`, `visao.py`, `__main__.py`, `config.toml` | **Verificacao 3, EXIT 0** (com controle negativo confirmando que a guarda reprova) |
| Nao tocar `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `tests/test_bosses.py` | Nenhum aparece no `git diff --stat` do plano |
| Nao commitar `calibration.json` | **Verificacao 4, EXIT 0** |
| FIRE-01, zero dependencia nova | **Verificacao 5, EXIT 0**; `test_mercado_firewall_de_fase.py` verde |
| Nunca `git commit --amend` | Sete commits lineares, nenhum reescrito |
| A analise LE o CSV e nunca o reescreve | `observacoes_do_arquivo` so abre em `"r"`; teste do 04-02 verde |
| Nao rodar a varredura do censo, nao usar glob em `recordings/` | Nada aqui toca `recordings/` |
| `.mercado/` do usuario intocada | Todo teste que persiste passa `pasta=tmp_path` |

## O que o proximo plano (04-04) consome

```python
from l2scanner.config import ler_watchlist_do_mercado
from l2scanner.mercado_analise import (
    ABAIXO_DA_MEDIANA, ACIMA_DA_MEDIANA, SEM_DESTAQUE, SERIES_NO_TOPO,
    Destaque, ModeloDeMercado, SerieNoConsole,
    nome_normalizado, ordenar_para_o_console,
)
from l2scanner.mercado_console import (
    MARCA_DA_WATCHLIST, SEGUNDOS_ENTRE_SECOES,
    formatar_centesimos, formatar_unitario_derivado, secao_do_vale_quanto,
)
```

Tres avisos para quem continua:

1. **`nome_normalizado` e o criterio de casamento que o 04-04 vai formalizar.** Ele ja
   existe, ja e exato (`casefold` + espacos colapsados) e ja tem teste provando que
   variante de encanto NAO casa. Nao escreva o segundo.
2. **`formatar_centesimos` e `formatar_unitario_derivado` sao a unica formatacao de
   dinheiro do projeto.** A margem de craft do ANAL-04 vai precisar delas, e uma
   segunda formatacao seria a que um dia esquece a marca `(derivado)`.
3. **A ordem do tick e um invariante, nao um detalhe.** Qualquer coisa que o ANAL-04
   acrescentar ao laco entra DEPOIS do passo 1, nunca antes — o passo 1 tem de ver o
   modelo como ele estava no comeco do tick.

## Self-Check: PASSED

Os arquivos citados existem em disco (`l2scanner/config.py`,
`l2scanner/mercado_analise.py`, `l2scanner/mercado_console.py`,
`l2scanner/mercado_modo.py`, `tests/test_mercado_console.py`,
`tests/test_mercado_modo.py` e este SUMMARY) e os sete commits existem no historico:
`8b5d9a7`, `83ae46e`, `12f968a`, `842f0de`, `7172061`, `374fd72`, `29593ff`.
