---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 05
subsystem: loot
tags: [loot, presenca, sugestao, d-13, somente-leitura, ast, tdd]

# Dependency graph
requires:
  - phase: 10-04
    provides: "`Fechamento`, `fechar_ocorrencias`, e o `texto_de_fechamento(sugestao=)` declarado e ignorado — o gancho que este plano preenche"
  - phase: 10-03
    provides: "`presenca.py` e o gate de AST parametrizado sobre os tres modulos"
  - phase: 10-03b
    provides: "o despacho generalizado — o `.join` que enche a lista que alimenta a sugestao"
  - phase: 08-loot-do-solo-boss
    provides: "`RegistroDeLoot.resumo`/`designar`/`consumir`, `responder_designacao`, e a pasta `.loot/` sem poda"
  - phase: 06-agenda-de-eventos
    provides: "`chave_da_ocorrencia`, `RegistroEmDisco.presentes`"
provides:
  - "`loot.sugerir_a_vez(registro, presentes) -> tuple[str, int] | None` — quem, entre os presentes, pegou menos, com desempate deterministico em tres niveis"
  - "`loot.responder_designacao(..., presenca=None)` — sufixo consultivo que GRAVA e avisa, e nunca recusa (D-13)"
  - "`presenca.texto_de_fechamento(..., sugestao=(slug, total))` — o parametro deixou de ser ignorado"
  - "`sessao._processar_agenda` e `__main__._fechar_listas_de_presenca` calculando a sugestao NA BORDA e passando adiante"
  - "`tests/test_loot.py::TestNenhumTipoDeArquivoNovoNaPastaDeLoot` — o gate de ESTADO da pasta sem poda (T-10-08)"
affects: []

# Actuals (#2632) — pareia com o `estimate` do plano. Base: chars/4 sobre o
# DIFF realizado em `l2scanner/` + `tests/` (29.918 chars), a MESMA escala que
# o plano usou. O plano estimou raw_tokens 29000 / tokens 58000; o diff real
# deu ~7,5k. Superestimativa de ~3,9x sobre o raw — a SEXTA seguida na mesma
# direcao nesta fase (10-01 ~3x, 10-02 ~4,5x, 10-03 ~4,3x, 10-03b ~3,3x,
# 10-04 ~3,3x, 10-05 ~3,9x). Seis planos errando para o mesmo lado, com a
# razao presa entre 3x e 4,5x, e um fator de correcao utilizavel e nao mais
# um palpite. O numero NAO foi arredondado para perto da estimativa.
actuals:
  tokens: 7479
  tasks: 2
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Funcao de DECISAO explicitamente somente-leitura contra um diretorio sem backup, com a propriedade afirmada por comparacao de estado (listagem da pasta antes/depois), e nao por leitura de codigo"
    - "Gate de FAMILIA de arquivo (`_familia(nome) -> prefixo | DESCONHECIDA:nome`) sobre um ciclo completo, com guarda contra prova vazia: pega um tipo de arquivo novo que nenhum teste de retorno pegaria"
    - "Desempate deterministico em tres niveis com o nivel do meio provado POR INVERSAO: removido do fonte, cai exatamente um teste, e o previsto"
    - "Sufixo consultivo depois da escrita (`grava -> le a lista -> acrescenta`), com comentario dizendo que ali nao pode nascer um `return` de recusa"
    - "Colecao vazia como AUSENCIA DE OPINIAO e nao como caso de erro: lista vazia nao produz sufixo, `presentes` vazio devolve `None`"

key-files:
  created: []
  modified:
    - l2scanner/loot.py
    - l2scanner/presenca.py
    - l2scanner/sessao.py
    - l2scanner/__main__.py
    - tests/test_loot.py
    - tests/test_presenca.py
    - tests/test_sessao.py

key-decisions:
  - "`sugerir_a_vez` mora no `loot.py` e recebe `presentes` por PARAMETRO. A direcao `presenca -> loot -> agenda` fica intacta; `loot.py` passou a importar `chave_da_ocorrencia` de `agenda`, que ja era permitido, e segue sem `comandos`, `sessao` e `presenca`"
  - "Desempate em TRES niveis — total, ultimo loot mais antigo, slug alfabetico. O nivel do meio nao e enfeite: sem ele o alfabeto decide sozinho e o mesmo nick pega duas vezes seguidas enquanto o empatado espera (T-10-19)"
  - "`.loot-<nick>` de quem nao joinou GRAVA e so ACRESCENTA o aviso. A ordem no fonte e `designar` -> consultar a lista -> concatenar, e o comentario diz por escrito que ali nao pode nascer um `return` (D-13, T-10-18)"
  - "Lista de presenca VAZIA nao produz sufixo nenhum: ninguem confirmou nada ainda. E o caso normal do `.loot-<nick>` mandado antes da chamada das 1h50, quando a party combina o revezamento no comeco do farm"
  - "`texto_de_fechamento(sugestao=)` mudou de `str` para `tuple[str, int]`. A funcao continua so FORMATANDO — ela recebe um par de valores e nunca um `RegistroDeLoot`, que e o que mantem `presenca.py` sem importar `loot.sugerir_a_vez`"
  - "Singular, plural e zero tratados na frase (`1 loot`, `3 loots`, `ainda nenhum`). E a linha que a party vai discutir em voz alta; `1 loots` a faria parecer quebrada justamente ali"
  - "`presenca=registro` foi passado dentro de `atender_comandos`, que ja recebe o `RegistroEmDisco` da agenda nos DOIS lacos — uma linha em vez de duas, sem parametro novo na assinatura"
  - "`_fechar_listas_de_presenca(loot=None)` com default: sem registro de loot a lista fecha e sai exatamente como no plano 10-04. Perder o desfecho da chamada por falta de uma estatistica opcional seria trocar a mensagem que importa pela que enfeita"

patterns-established:
  - "Prova por inversao aplicada a um desempate: o nivel do meio foi removido do fonte, a suite rodou, caiu exatamente `test_empate_no_total_desempata_pelo_ultimo_mais_antigo`, e o nivel foi restaurado"
  - "Gate de estado sobre diretorio sem backup: classificar por FAMILIA de prefixo e afirmar `familias <= FAMILIAS_DE_HOJE`, com um teste-controle que planta um arquivo de familia nova e exige que o classificador o pegue"

requirements-completed: [PRES-14, PRES-15]

coverage:
  - id: D1
    description: "A vez do proximo loot e SUGERIDA entre quem estava na lista fechada (D-13)"
    requirement: "PRES-14"
    verification:
      - kind: unit
        ref: "tests/test_loot.py#TestSugerirAVez::test_escolhe_quem_pegou_menos"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestSugerirAVez::test_ninguem_de_fora_da_lista_e_sugerido"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_a_lista_fechada_sai_com_a_sugestao_de_loot"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao"
        status: pass
    human_judgment: false
  - id: D2
    description: "`.loot-<nick>` de quem nao joinou GRAVA do mesmo jeito e a resposta so acrescenta o aviso — nunca recusa (D-13, T-10-18)"
    requirement: "PRES-15"
    verification:
      - kind: unit
        ref: "tests/test_loot.py#TestDesignacaoComListaDePresenca::test_quem_NAO_joinou_e_GRAVADO_e_so_leva_o_aviso (le `registro.designacao()` de volta do disco)"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestDesignacaoComListaDePresenca::test_nenhum_caminho_devolve_RECUSA_por_causa_da_lista (varre os tres estados da lista)"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestDesignacaoComListaDePresenca::test_a_substituicao_e_o_aviso_convivem"
        status: pass
    human_judgment: false
  - id: D3
    description: "A fase nao cria nenhum tipo de arquivo novo em `.loot/`, a pasta sem poda e sem backup (T-10-08)"
    verification:
      - kind: unit
        ref: "tests/test_loot.py#TestNenhumTipoDeArquivoNovoNaPastaDeLoot::test_o_ciclo_completo_nao_inventa_tipo_de_arquivo (designar, consumir, encher a lista, fechar, sugerir)"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestNenhumTipoDeArquivoNovoNaPastaDeLoot::test_a_prova_pega_de_verdade_uma_familia_nova (guarda contra prova vazia)"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestSugerirAVez::test_nao_escreve_NADA_na_pasta_sem_poda (listagem da pasta antes/depois)"
        status: pass
    human_judgment: false
  - id: D4
    description: "`loot.py` continua sem importar `comandos`, `sessao` ou `presenca`, e sem relogio proprio"
    verification:
      - kind: unit
        ref: "tests/test_presenca.py#TestDirecaoDeImportacao::test_loot_nunca_importa_presenca (AST, nunca grep)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_nenhum_now_de_datetime_na_arvore[loot.py]"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestDirecaoDeImportacao::test_o_pacote_inteiro_importa"
        status: pass
    human_judgment: false
  - id: D5
    description: "A sugestao e deterministica: as mesmas entradas produzem sempre o mesmo nome (T-10-19)"
    verification:
      - kind: unit
        ref: "tests/test_loot.py#TestSugerirAVez::test_empate_total_desempata_pelo_alfabeto_e_e_ESTAVEL (dois `RegistroDeLoot` sobre a mesma pasta)"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py#TestSugerirAVez::test_empate_no_total_desempata_pelo_ultimo_mais_antigo (provado por inversao: removido o nivel, cai so ele)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Sem registro de loot a mensagem de fechamento sai exatamente como no plano 10-04"
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestPresencaNoTick::test_sem_registro_de_loot_a_mensagem_sai_como_no_plano_10_04 (afirma a string inteira)"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestTextoDeFechamento::test_sugestao_none_nao_acrescenta_nada"
        status: pass
    human_judgment: false
  - id: D7
    description: "O ciclo completo no WhatsApp de verdade — a costura com o Chatwoot que nenhum teste offline alcanca"
    verification: []
    human_judgment: true
    rationale: "Os sete itens numerados do `<human-check>` da Tarefa 2 estao reproduzidos VERBATIM na secao `Human Verification Pendente` abaixo, para o verificador da fase colher no `10-UAT.md`. `workflow.human_verify_mode` deste projeto e `end-of-phase`, entao nao houve checkpoint no meio do caminho."

# Metrics
duration: 25min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 05: A lista sugere a vez do loot Summary

**A lista fechada passou a nomear quem deveria pegar o proximo loot — escolhendo entre quem confirmou, com desempate deterministico em tres niveis para as duas instancias nunca discordarem — e atravessou a pasta `.loot/`, que nunca e podada e nao tem backup, em modo estritamente somente-leitura, provado por comparacao do conjunto de familias de arquivo antes e depois de um ciclo completo.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 de 2
- **Files modified:** 7 | **created:** 0
- **Suite:** 976 -> **1003 passed, 2 skipped** (27 testes novos, nenhum afrouxado)
- **Commits:** 4 (`01e118d` RED, `8aef004` GREEN, `a2ab0e2` RED, `a2cc13d` GREEN)

## Accomplishments

- **A pasta sem poda saiu como entrou, e isso esta afirmado por ESTADO.** `TestNenhumTipoDeArquivoNovoNaPastaDeLoot` roda o ciclo inteiro da fase contra uma pasta temporaria — designar, consumir, encher a lista de presenca, fechar, sugerir, formatar a mensagem — e classifica cada arquivo resultante por FAMILIA de prefixo, exigindo `familias <= {"pegou_", "nick_", "proximo.json"}`. Medido de fora da suite, o ciclo produz exatamente `['nick_kaus', 'pegou_2026-08-25-2000_kaus']`, e uma segunda chamada de `sugerir_a_vez` sobre a mesma pasta nao muda um byte. Um `sugerir` que gravasse um cache ou um "ja sugeri este boss" passaria em todos os testes de retorno e criaria, no unico diretorio permanente do projeto, um tipo de arquivo que nenhum comando alcanca depois — e por isso o gate tem um teste-controle que planta `sugestao_2026-08-25-2000` e exige que o classificador o pegue.
- **O desempate do meio foi provado por INVERSAO, e nao por leitura.** O nivel "ultimo loot mais antigo" foi REMOVIDO do fonte e a suite rodou: caiu exatamente um teste — `test_empate_no_total_desempata_pelo_ultimo_mais_antigo` — e nenhum outro dos 1002 restantes. O nivel foi restaurado e os 1003 voltaram ao verde. Sem ele o alfabeto decidiria sozinho e o `Kaus` pegaria duas vezes seguidas enquanto o `TioMad` do mesmo total esperaria, que e o rodizio quebrado que o registro existe para consertar.
- **O `.loot-<nick>` continua sendo a ultima palavra, e isso e uma varredura e nao um caso.** `test_nenhum_caminho_devolve_RECUSA_por_causa_da_lista` percorre os tres estados possiveis da lista — vazia, com o designado fora, com o designado dentro — e em todos afirma que `registro.designacao()` foi lida de volta do DISCO com o nick certo e que a resposta contem a confirmacao. A ordem no fonte e `designar` primeiro, consultar a lista depois, com comentario dizendo por escrito que ali nao pode nascer um `return` de recusa (D-13, T-10-18).
- **Lista vazia nao tem opiniao, nos dois lados.** `presentes` vazio faz `sugerir_a_vez` devolver `None`, e uma lista de presenca vazia nao acrescenta sufixo nenhum ao `.loot-<nick>`. O segundo caso e o NORMAL, nao o excepcional: a party combina o revezamento no comeco do farm, muito antes da chamada das 1h50, e avisar ali seria ruido sobre uma lista que nem existe. Medido: `.loot-fantasma` as 20:05, com a lista das 22:00 vazia, sai exatamente `"Fantasma pega o loot do proximo Solo Boss, as 22:00."`; com a lista cheia e sem ele, ganha `" (Fantasma nao esta na lista de presenca deste boss, mas anotei.)"` — e a designacao gravada e `fantasma` nos dois.
- **A posicao do fechamento no tick deixou de ser convencao e virou dependencia real.** O plano 10-04 pos o fechamento DEPOIS do `self.loot.consumir(agora)` explicando que o 10-05 dependeria disso. Agora depende, e ha teste: `test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao` designa o `kaus` para o proprio boss das 10:00, e no tick das 10:00 o consumo registra o loot dele ANTES de a lista fechar — a sugestao ja o enxerga com um loot a mais e passa a vez para o outro. Invertida a ordem, o bot sugeriria justamente quem acabou de pegar.
- **O gancho do 10-04 foi preenchido sem ser redesenhado.** `texto_de_fechamento(sugestao=)` nasceu declarado e ignorado com dois testes proprios; este plano mudou apenas o TIPO (de `str` para o par `(slug, total)`) e o corpo da formatacao. A funcao continua so formatando — ela recebe um par de valores e nunca um `RegistroDeLoot` — e e isso que mantem `presenca.py` sem importar `loot.sugerir_a_vez`.
- **A frase nova entrou na rede que ja existia.** As TRES formas da sugestao (`ainda nenhum`, `1 loot`, `3 loots`) foram acrescentadas a `TestFormaDoTexto.todas_as_frases`, entao passam pelos mesmos gates de "sem acento", "sem quebra de linha" e "nao vazia" que as doze frases anteriores. Uma varredura independente sobre TODAS as linhas adicionadas em `l2scanner/` e `tests/` confirmou zero caracteres acentuados (so travessoes em prosa, como o resto do arquivo).
- **A direcao de importacao ficou intacta, e o gate seguiu por AST.** `loot.py` passou a importar `chave_da_ocorrencia` de `agenda` — dentro da direcao permitida — e continua sem `comandos`, `sessao` e `presenca`. Os 9 testes de `TestDirecaoDeImportacao` e `TestSemRelogioProprio` seguem verdes e seguem baseados em `ast.parse`, o que importa porque as docstrings novas de `loot.py` CITAM os tres nomes proibidos de proposito, para explicar a restricao — um grep daria positivo justamente na documentacao que a protege.
- **Zero dependencia nova.** `git diff --name-only` contra a base sobre `pyproject.toml`, `requirements.txt` e `uv.lock` devolve vazio (T-10-SC).

## Task Commits

1. **Tarefa 1 RED: a vez entre os presentes, e a pasta que nao pode crescer** — `01e118d` (test)
2. **Tarefa 1 GREEN: `sugerir_a_vez`, somente leitura e deterministica** — `8aef004` (feat)
3. **Tarefa 2 RED: a sugestao na mensagem, e o aviso que obedece** — `a2ab0e2` (test)
4. **Tarefa 2 GREEN: a frase, a borda nos dois lacos, e o `presenca=` no `.loot-`** — `a2cc13d` (feat)

## Files Created/Modified

- **`l2scanner/loot.py`** (+90) — `sugerir_a_vez` na secao de funcoes puras, com docstring de tres itens (por que SUGERE e nao manda e nao grava nada; por que o desempate e deterministico, citando o `encaixar_na_agenda`; por que `presentes` entra por parametro); `responder_designacao(presenca=None)` com o sufixo consultivo DEPOIS da gravacao e o comentario de que ali nunca nasce um `return`; `chave_da_ocorrencia` acrescentado ao import de `agenda`.
- **`l2scanner/presenca.py`** (+22 / -9) — `texto_de_fechamento(sugestao=)` mudou de `str` para `tuple[str, int]` e passou a formatar a frase, com a grafia do `config.toml` pelo mapa `nomes` e singular/plural/zero tratados; o paragrafo "nasce declarada e ignorada" foi trocado por um que nomeia os dois chamadores.
- **`l2scanner/sessao.py`** (+13 / -1) — `sugerir_a_vez` no import de `loot`; `_processar_agenda` calcula a sugestao NA BORDA quando `self.loot` existe e a passa ao texto, com comentario dizendo por que a leitura acontece ali.
- **`l2scanner/__main__.py`** (+22 / -3) — `sugerir_a_vez` no import; `_fechar_listas_de_presenca(..., loot=None)` calculando a sugestao por fechamento; `loot=registro_de_loot` na chamada do laco `--so-agenda`; `presenca=registro` no ramo `LOOT_DESIGNAR` de `atender_comandos`, que serve os DOIS lacos com uma linha so.
- **`tests/test_loot.py`** (+383) — `TestSugerirAVez` (10), `TestNenhumTipoDeArquivoNovoNaPastaDeLoot` (2), `TestDesignacaoComListaDePresenca` (8); imports de `RegistroEmDisco`/`chave_da_ocorrencia` e de `presenca` para o teste de ciclo completo.
- **`tests/test_presenca.py`** (+41 / -10) — os dois testes de `sugestao` do 10-04 acompanharam a mudanca de tipo; dois testes novos (grafia do config na sugestao, singular/plural/zero); as tres formas da frase entraram em `todas_as_frases`.
- **`tests/test_sessao.py`** (+103) — cinco casos novos em `TestPresencaNoTick` e o helper `_loot_com`.

## Decisions Made

- **A funcao mora no `loot.py` e recebe a lista por parametro.** Poe-la no `presenca.py` teria sido mais curto — a lista ja esta la — e teria custado o import de `loot` para dentro de uma funcao que decide sobre estatistica de loot, ou pior, o import inverso. A direcao `presenca -> loot -> agenda` e fixa porque um ciclo aqui nao degrada nada: mata os dois modulos com `ImportError` no arranque. `loot.py` ganhou `chave_da_ocorrencia` de `agenda`, que ja era permitido, e o gate de AST continua verde sobre os tres modulos.
- **Tres niveis de desempate, e o do meio e o que faz o recurso valer.** Total sozinho empata o tempo todo com uma party de 4-8 pessoas em rodizio; total + alfabeto e deterministico mas injusto de um jeito visivel, porque o mesmo nick ganharia todos os empates para sempre. O nivel "ultimo loot mais antigo" e o que transforma a sugestao em rodizio de verdade — e foi o unico dos tres cuja necessidade nao era obvia, entao foi o que ganhou prova por inversao.
- **Grava primeiro, consulta depois, e o comentario diz por que.** A propriedade que D-13 exige nao e sobre o texto, e sobre a estrutura: nenhum caminho pode devolver recusa por causa da lista. Consultar a lista ANTES do `designar` deixaria o codigo numa forma que convida, na primeira manutencao, um `return` no meio — e a party perderia a designacao no momento em que mais precisa dela, com o boss nascendo e alguem que chegou sem avisar.
- **Lista vazia nao produz sufixo.** A alternativa — avisar sempre que a pessoa nao esta na lista — pareceria mais consistente e seria pior: o `.loot-<nick>` mandado antes da chamada das 1h50 e o caso NORMAL, e ele passaria a sair sempre com um aviso sobre uma lista que ainda nao existe. Um aviso que aparece quase sempre e um aviso que ninguem le.
- **`presenca=registro` foi passado dentro de `atender_comandos`.** O plano pedia "nos dois lacos"; a funcao ja recebe o `RegistroEmDisco` da agenda dos dois, entao uma linha resolve e nenhuma assinatura nova aparece. Acrescentar um parametro `presenca=` a `atender_comandos` teria duplicado, na costura, a informacao que ela ja tem — e a costura e onde os erros deste projeto moram.
- **`_fechar_listas_de_presenca` ganhou `loot=None` com default.** O `--so-agenda` e o modo de quem esta longe do jogo, e a lista fechada e o desfecho da pergunta que a chamada fez no grupo 1h50 antes. Amarra-la a existencia de uma pasta de loot faria a party perder a resposta por causa de um extra.
- **Singular, plural e zero tratados na frase.** `"1 loots"` e `"0 loots"` leem como bug, e esta e literalmente a linha que a party vai discutir em voz alta quando o boss nascer. Tres ramos de string custam nada e evitam que a mensagem mais visivel da fase seja a que parece quebrada.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O teste da chave da ocorrencia nao exercitava a chave — ele passava pela regra de lista vazia**

- **Found during:** Tarefa 2, GREEN
- **Issue:** `test_a_lista_consultada_e_a_do_boss_ALVO_e_nao_a_de_outro` punha o `fantasma` na lista das 12:00 e designava para o boss das 10:00, esperando o aviso. Mas a lista das 10:00 ficava VAZIA, e o silencio que o teste teria observado viria da regra "lista vazia nao tem opiniao", nao da comparacao de chave. O teste falhou — e falhou por um defeito NO TESTE: ele nao podia provar o que dizia provar, porque nunca chegava a comparar chave nenhuma.
- **Fix:** A lista das 10:00 passou a ter o `kaus`, e o `fantasma` ficou so na das 12:00. Agora o aviso sai porque a chave das 10:00 nao contem o `fantasma`, que e a propriedade que o teste nomeia. A docstring passou a dizer por que a lista alvo precisa ter alguem: com ela vazia o teste passaria sem provar nada sobre a chave.
- **Files modified:** `tests/test_loot.py`
- **Verification:** `python -m pytest tests/test_loot.py tests/test_sessao.py tests/test_presenca.py -q` -> 257 passed.
- **Committed in:** `a2cc13d`

**2. [Interface — previsto no plano] `texto_de_fechamento(sugestao=)` mudou de `str` para `tuple[str, int]`**

- **Found during:** Tarefa 2
- **Issue:** Os dois testes do plano 10-04 (`test_sugestao_none_nao_acrescenta_nada`, `test_sugestao_preenchida_entra_no_fim`) passavam uma string pronta.
- **Fix:** Nao e desvio de escopo — o plano 10-05 manda explicitamente formatar o par `(slug, total)` usando o mapa `nomes`. Os dois testes acompanharam a mudanca de tipo preservando o que cada um afirma (`None` nao acrescenta nada; preenchida entra no fim), e dois testes novos cobrem a grafia do config e as tres formas da frase. **Nenhum teste foi afrouxado:** a cobertura da funcao subiu de 2 casos de `sugestao` para 4, mais 3 formas dentro de `todas_as_frases`.
- **Files modified:** `tests/test_presenca.py`, `l2scanner/presenca.py`
- **Committed in:** `a2cc13d`

Nenhuma outra deviacao: o codigo de producao dos quatro arquivos saiu como o plano descreveu.

## Itens Fora de Escopo (nao consertados)

`python -m ruff check` sobre o repositorio inteiro devolve 4 erros — 2 `E741` em `l2scanner/visao.py` e 2 `F401` em `tests/test_sessao.py`. Todos sao **pre-existentes**, confirmado rodando o ruff sobre a versao dos arquivos no commit base `e8d8b1b`, e os dois `F401` ja estao registrados no `deferred-items.md` desta fase desde o plano 10-04. Nenhum arquivo tocado por este plano tem erro: `ruff check` sobre os sete devolve `All checks passed`.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. As quatro mitigacoes com disposicao `mitigate` estao afirmadas por teste:

| Threat | Disposicao | Onde esta afirmada |
|---|---|---|
| T-10-08 (`.loot/`, estatistica sem poda e sem backup) | mitigate | `TestNenhumTipoDeArquivoNovoNaPastaDeLoot::test_o_ciclo_completo_nao_inventa_tipo_de_arquivo` + `TestSugerirAVez::test_nao_escreve_NADA_na_pasta_sem_poda` (ambos comparam ESTADO da pasta) |
| T-10-18 (lista virando autoridade sobre o loot) | mitigate | `TestDesignacaoComListaDePresenca::test_quem_NAO_joinou_e_GRAVADO_e_so_leva_o_aviso` e `::test_nenhum_caminho_devolve_RECUSA_por_causa_da_lista` |
| T-10-19 (sugestao divergente entre as duas instancias) | mitigate | `TestSugerirAVez::test_empate_total_desempata_pelo_alfabeto_e_e_ESTAVEL`, com o nivel do meio provado por inversao |
| T-10-20 (contagem de loot de terceiros no grupo) | accept | Inalterado: o grupo ja recebe `Loot: X` no aviso de antecedencia desde a Fase 8, e o `.<nick>` ja responde a contagem. Nenhuma informacao nova e revelada |
| T-10-SC (instalacao de pacote) | mitigate | `git diff --name-only e8d8b1b -- pyproject.toml requirements.txt uv.lock` devolve VAZIO |

## Human Verification Pendente

`workflow.human_verify_mode` deste projeto e `end-of-phase`, entao esta fase nao teve checkpoint no meio do caminho. Os sete itens abaixo sao o bloco `<verify><human-check>` da Tarefa 2 do `10-05-PLAN.md`, **reproduzidos verbatim** para o verificador da fase colher no `10-UAT.md`.

> **O ciclo completo no WhatsApp de verdade — a costura que nenhum teste offline alcanca.**
>
> Toda a fase e demonstravel sem jogo e sem rede, e esta demonstrada: a suite roda
> inteira offline. O que falta e a outra coisa — a costura com o Chatwoot real,
> que e historicamente onde os defeitos deste projeto moram (`__main__.py` com
> 19-20% de cobertura, os 3 de 3 warnings do code review morando la, a ponte
> Baileys sem ingestao de grupo descoberta so por medicao).
>
> **Antes de comecar, confira que existe:** `CHATWOOT_TELEFONES_COMANDO` e
> `CHATWOOT_ETIQUETA_COMANDO` no `.env`, a conversa privada com a etiqueta `CP`
> no painel do Chatwoot, e pelo menos um `[[membro]]` no `config.toml` com um
> telefone real. Sem isso nada abaixo pode acontecer.
>
> Rode o scanner (ou so `--so-agenda`, que basta e nao exige o jogo aberto) e
> confira no celular:
>
> 1. A chamada chega no grupo 1h50 antes do proximo Solo Boss, com o horario
>    certo, num texto que diz para responder no privado.
> 2. Um party-mate manda `.join` no privado do bot e recebe de volta uma linha
>    curta citando o horario do boss.
> 3. O grupo recebe a confirmacao com o NICK do `config.toml` — nao com o nome
>    do contato do WhatsApp.
> 4. Um segundo `.join` da mesma pessoa responde no privado e NAO aparece no
>    grupo.
> 5. Um `.leave` tira da lista e o grupo fica sabendo.
> 6. No horario do boss o grupo recebe a lista fechada com a sugestao de loot.
>    **E, com ninguem na lista, NENHUMA mensagem chega.** Confira os dois
>    estados: e a promessa de silencio que voce tomou ao desligar
>    `avisar_no_horario` no Solo Boss.
> 7. Esse mesmo party-mate manda `.corrigir-Fulano` e o bot NAO obedece. Este e
>    o item de seguranca da fase; o teste automatico o prova, mas ele merece ser
>    visto.
>
> Se algo divergir, registre o que foi observado — horario, conversa e texto
> exato — antes de propor conserto. E a disciplina de medir antes de opinar que
> o projeto ja segue.

Para referencia do item 6, a mensagem medida fora da suite num ciclo completo foi:

```
Solo Boss das 20:00 comecando. Confirmaram: J4guar, Kaus, TioMad. Sugestao de loot: J4guar (ainda nenhum).
```

## Known Stubs

Nenhum. O unico stub declarado da fase — `texto_de_fechamento(..., sugestao=)` nascido sem chamador no plano 10-04 — **foi resolvido por este plano**, que e exatamente o que aquela entrada previa. Nenhum valor vazio codificado, nenhum `TODO`/`FIXME`/`placeholder` novo, nenhum teste com `skip` acrescentado (os 2 `skipped` da suite sao os mesmos de antes desta fase).

## Self-Check: PASSED

- `l2scanner/loot.py` — FOUND (`sugerir_a_vez` definida; `presenca=None` em `responder_designacao`; `chave_da_ocorrencia` importado de `agenda`)
- `l2scanner/presenca.py` — FOUND (`texto_de_fechamento` formatando o par `(slug, total)`)
- `l2scanner/sessao.py` — FOUND (`sugerir_a_vez` importado e chamado em `_processar_agenda`)
- `l2scanner/__main__.py` — FOUND (`loot=registro_de_loot` no `_fechar_listas_de_presenca`; `presenca=registro` no ramo `LOOT_DESIGNAR`)
- `tests/test_loot.py` — FOUND (`TestSugerirAVez`, `TestNenhumTipoDeArquivoNovoNaPastaDeLoot`, `TestDesignacaoComListaDePresenca`)
- `tests/test_presenca.py` — FOUND (4 casos de `sugestao` em `TestTextoDeFechamento`; 3 formas em `todas_as_frases`)
- `tests/test_sessao.py` — FOUND (5 casos novos em `TestPresencaNoTick`)
- Commits `01e118d`, `8aef004`, `a2ab0e2`, `a2cc13d` — FOUND em `git log e8d8b1b..HEAD`
- `python -m pytest tests/ -q` -> **1003 passed, 2 skipped**
- `python -c "import l2scanner.loot, l2scanner.presenca, l2scanner.__main__"` -> ok, sem ciclo
- `python -m ruff check` sobre os SETE arquivos tocados -> **All checks passed**
- `git diff --name-only e8d8b1b -- pyproject.toml requirements.txt uv.lock` -> **vazio** (zero dependencia nova)
