---
phase: 04-modo-mercado-an-lise-e-console
plan: 04
subsystem: analise
tags: [receita, margem-de-craft, staleness, fraction, casamento-exato, toml, console, stdlib]
status: complete

requires:
  - phase: 04-modo-mercado-an-lise-e-console
    plan: 02
    provides: "`unitario` (Fraction), `menor_pedido_visivel`, `mediana_dos_unitarios`, `recencia_do_preco`, `Evidencia` e os pisos declarados como ESCOLHA"
  - phase: 04-modo-mercado-an-lise-e-console
    plan: 03
    provides: "`ModeloDeMercado`, `nome_normalizado`, `ordenar_para_o_console`, `secao_do_vale_quanto`, `SEGUNDOS_ENTRE_SECOES` e o laco de `mercado_modo` com `ler_watchlist_do_mercado`"
  - phase: 03-persist-ncia-de-observa-es
    provides: "`ObservacaoLida` com `chave_da_serie`, `nome_exibido`, `primeira_vez`, `total_em_centesimos` e `quantidade`"
provides:
  - "`ReceitaInvalida`, `Receita`, `ComponenteDaReceita` e `ler_receitas` no FIM de `l2scanner/config.py`"
  - "`margem_de_craft`, `resolver_o_nome`, `MargemDeCraft`, `LinhaDaMargem`, `ResolucaoDeNome`, `componente_esta_velho` e `HORAS_PARA_MARCAR_COMPONENTE_VELHO` em `mercado_analise.py`"
  - "`secao_da_margem`, `AVISO_DE_OFERTA_TALVEZ_COMPRADA`, `MARCA_DO_COMPONENTE_VELHO`, `COLUNA_DO_NOME` e `LARGURA_DO_AVISO` em `mercado_console.py`"
  - "`laco_do_mercado(..., receitas=None)`: as receitas lidas UMA vez no arranque, com recusa de arranque para receita torta"
affects: [04-05, ANAL-04]

actuals:
  tokens: 22487
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Casamento EXATO sobre `nome_normalizado` quando o texto e DIGITADO por humano; similaridade fuzzy so quando os dois lados sao leituras do MESMO pixel"
    - "`difflib.get_close_matches` para SUGERIR na mensagem de recusa, nunca para decidir o desfecho"
    - "Estado quebrado sem valor parcial: `_margem_quebrada` devolve `linhas=()` para que quem desenha nao tenha o que somar"
    - "`isinstance(valor, bool)` ANTES do teste numerico, replicado de `_horas_de_respawn` para o segundo lugar do projeto onde o furo apareceria"
    - "Constante FORA do `__all__` quando um criterio de verificacao ancora na primeira ocorrencia do nome no fonte"
    - "Coluna de alinhamento como constante (`COLUNA_DO_NOME`) e largura de rotulo derivada do recuo, para hierarquia por indentacao sem escalonar as colunas"

key-files:
  created:
    - tests/test_mercado_receitas.py
  modified:
    - l2scanner/config.py
    - l2scanner/mercado_analise.py
    - l2scanner/mercado_console.py
    - l2scanner/mercado_modo.py

key-decisions:
  - "`ReceitaInvalida` e CLASSE PROPRIA e nao `AgendaInvalida` reusada, ao contrario de `ler_membros` e `ler_watchlist_do_mercado`. A razao e o destino do `except`: o laco CAPTURA a `AgendaInvalida` da watchlist de proposito, porque a watchlist so promove series no console e um erro nela nao pode custar a coleta da noite. A receita e uma CONTA, e uma conta torta que degradasse para 'sem margem' sairia calada — o usuario descomentaria um bloco, nao veria margem e nao teria uma linha em lugar nenhum dizendo por que. Uma classe separada e o que permite tratar os dois casos diferente sem inspecionar texto de mensagem"
  - "A recusa de arranque por receita torta mora JUNTO da leitura da watchlist, DEPOIS do portao de OCR e da calibracao mas ANTES de qualquer captura. Recusar ali nao custa coleta nenhuma (nenhum frame foi capturado) e mantem as duas leituras de `config.toml` no mesmo lugar"
  - "`rende` e OBRIGATORIO e nao opcional com padrao 1, e `componentes` vazio ou ausente tambem recusa. Um padrao silencioso de `rende = 1` daria uma margem cinco vezes menor que a real para quem crafta cinco de cada vez; `componentes` vazio daria uma 'margem' igual ao proprio preco do produto"
  - "NAO ESTAVA NO PLANO: `rende` e `quantidade` recusam FRACIONARIO alem de booleano. `rende = 1.5` nao descreve craft nenhum, e aceita-lo faria a margem depender de um arredondamento que ninguem escolheu. `1.0` cai junto de proposito — aceitar o float redondo e recusar o quebrado seria uma regra que o usuario descobre por tentativa"
  - "O PRODUTO concorre com os componentes na disputa de 'evidencia mais velha'. O plano falava em staleness por COMPONENTE, mas um produto com preco de uma semana atras estraga a conta exatamente como um ingrediente estragaria, e promover so componentes esconderia metade dos casos"
  - "`HORAS_PARA_MARCAR_COMPONENTE_VELHO` ficou FORA do `__all__` de proposito, ao contrario dos pisos de evidencia que entram. Com o nome na lista, o criterio de grep do plano (`f.index(...)` mais 900 caracteres) ancoraria no `__all__` e a janela cairia no bloco dos pisos, que ja dizia 'ESCOLHA' desde o 04-02 — o criterio passaria com a constante muda. Fora da lista, `index == rindex == 34615`, medido, e o criterio mede o que diz medir"
  - "A margem pela mediana so sai INTEIRA ou nao sai. Misturar mediana de um lado com menor do outro produziria um terceiro numero que nao e nem uma coisa nem outra"
  - "O estado quebrado devolve `linhas=()` e nenhum valor parcial. Devolver as linhas que ja tinham resolvido convidaria quem desenha a somar o que deu, e 'a margem sem o Leonard' e precisamente o numero plausivel e errado que a quebra existe para impedir"
  - "A advertencia do cabecalho sai QUEBRADA em 76 colunas. A primeira versao saiu numa linha de ~180 caracteres que rolava para fora da janela do console — uma advertencia que ninguem le nao adverte, e ela e a unica defesa contra o numero abaixo dela parecer acionavel"

patterns-established:
  - "Quando o texto de um lado do casamento e DIGITADO por um humano e o do outro vem de OCR, o casamento e exato e a ambiguidade QUEBRA; similaridade calibrada so vale entre duas leituras do MESMO pixel"
  - "Um criterio de verificacao que ancora na primeira ocorrencia de um nome no fonte deve ser protegido mantendo o nome fora do `__all__` — ou ele mede a lista em vez do codigo"
  - "Ao apendicar num modulo com contencao de diff, o import novo mora no proprio bloco apendicado com `# noqa: E402`, e o `git diff --numstat` do arquivo fica com 0 remocoes"

requirements-completed: [ANAL-04]
---

# Phase 4 Plan 4: Margem de Craft com Staleness por Componente — Summary

A margem do ANAL-04 sai sobre menor pedido visivel dos dois lados, com a idade de cada
componente na propria linha e a mais velha promovida a linha da margem — e ela **quebra,
nomeando o que falta, em vez de adivinhar** quando um ingrediente nao tem observacao ou
quando o nome digitado casa com duas series.

## O que foi entregue

| Task | Entrega | Commits |
|---|---|---|
| 1 | `ReceitaInvalida`, `Receita`, `ComponenteDaReceita` e `ler_receitas` no FIM de `config.py` — 279 linhas ACRESCENTADAS, 0 removidas | `e643e1a` (RED), `60b563d` (GREEN) |
| 2 | `margem_de_craft` e `resolver_o_nome` em `mercado_analise.py`, com as cinco limitacoes na docstring publica | `7038f6c` (RED), `8db0219` (GREEN) |
| 3 | `secao_da_margem` em `mercado_console.py` e a fiacao no laco de `mercado_modo.py` | `c0039cf` (RED), `57b80e7` (GREEN) |

## O desenho, como ele sai

```
**********************************************************
  MARGEM DE CRAFT                                  [21:15]
**********************************************************

  ATENCAO: o programa nao sabe se estas ofertas ainda existem - o registro
  nao anota desaparecimento. Um pedido de 20 min atras pode ter sido
  comprado ha 19. Confira na tela antes de agir.

  Dragon Belt (rende 1)
    produto     Dragon Belt           menor 1.480,00 por 1 unidade | n=1 | ha 22 min
      - 5x      Common Aztac          menor 62,00 por 48 unidades | n=1 | ha 8 min
      - 20x     Leonard               menor 4,50 por 100 unidades | n=1 | ha 3 dias  <--
    margem      +1.472,64 (derivado) | evidencia mais velha: ha 3 dias (Leonard)
```

E quando ela quebra, o motivo ocupa o lugar do numero:

```
  Dragon Belt (rende 1)
    sem margem: nao ha observacao nenhuma de 'Leonarde', entao a margem inteira
    nao sai. Calcular sem ele daria um numero plausivel e errado. Os nomes
    parecidos que eu tenho: Leonard.
```

## O controle negativo do casamento fuzzy — MEDIDO nesta sessao

A decisao mais importante do plano era **nao** usar `mercado_catalogo.similaridade`. O
teste roda a alternativa errada e afirma que ela erra, com numeros medidos e nao estimados:

| Par | Similaridade | Corte 0,8947 |
|---|---|---|
| `+3 Dragon Belt` x `+4 Dragon Belt` | **0,9286** | CASARIA — series deliberadamente separadas |
| `B-grade Gemstone` x `C-grade Gemstone` | **0,9375** | CASARIA — a fusao ABERTA desde a Fase 2 |
| `Leonard` x `Leonarde` | **0,9333** | CASARIA — um erro de digitacao ADOTADO em silencio |
| `+3 Dragon Belt` x `Dragon Belt` | **0,88** | nao casaria |

A ultima linha e a que fecha o argumento: o fuzzy **nao erra sempre, erra de forma
imprevisivel**, entao o usuario nao consegue nem aprender a regra.

**Correcao de rota registrada:** a primeira redacao deste teste afirmava que
`+3 Dragon Belt` x `Dragon Belt` cruzaria o corte. Medido, da **0,88** — abaixo. A
afirmacao estava errada e foi trocada pelos tres pares que realmente cruzam. Um numero que
cai precisa dizer que caiu.

## Criterios `<automated>` — cada um rodado como escrito

| Criterio | Resultado real |
|---|---|
| T1: `pytest tests/test_mercado_receitas.py -x -q` | **23 passed** |
| T1: `pytest tests/test_mira_da_janela.py tests/test_calibracao_generica.py -x -q` | **42 passed** |
| T2: `pytest tests/test_mercado_receitas.py tests/test_mercado_analise.py -x -q` | **105 passed** |
| T3: `pytest tests/test_mercado_receitas.py tests/test_mercado_console.py tests/test_mercado_modo.py -x -q` | **156 passed** |
| V1: `pytest .../receitas .../console .../analise -x -q` | **160 passed** |
| V2: `pytest tests/ --ignore=tests/test_agenda.py -q` | **3077 passed, 23 skipped** |
| V3 config.toml intocado | exit 0 — literal E contra a base |
| V4 rastreador/visao/`__main__` intocados | exit 0 — literal E contra a base |
| V5 calibration.json nao escrito | exit 0 |
| V6 requirements.txt intocado | exit 0 |
| `ler_receitas(Path('nao-existe.toml')) == []` | exit 0 |
| `HORAS_PARA_MARCAR_COMPONENTE_VELHO == 24` | exit 0 |
| `'escolha' in f[i:i+900]` | exit 0 — e agora pelo motivo certo |
| `'similaridade' in getsource(margem_de_craft)` | exit 0 |

### Os tres criterios que se revelaram vacuos ou fracos, com o controle negativo medido

**1. `assert 'bool' in inspect.getsource(c)` (Task 1) — VACUO, medido.**
`inspect.getsource(c)` e o modulo `config.py` INTEIRO, e `_horas_de_respawn` ja usa
`isinstance(valor, bool)` desde a fase de bosses. **Controle negativo:** rodado na arvore
pristina, ANTES de uma linha ser escrita, com `hasattr(config, 'ler_receitas') == False` —
**saiu com exit 0**. Ele passaria com a funcao inexistente.
*Discriminante acrescentado ao lado, nao no lugar:*
`TestAGuardaDoBooleanoEstaNO_FONTE` afirma `isinstance` e `bool` no fonte de
`_inteiro_positivo_da_receita` (a funcao NOVA) **e a ORDEM** (`fonte.index("bool") <
fonte.index("<= 0")`), que e a unica coisa que importa. Mais o controle negativo mecanico:
o teste carrega o TOML e afirma que `True` passa por `int`, passa por `> 0` e viraria `1`.

**2. `f.index('HORAS_PARA_MARCAR_COMPONENTE_VELHO')` mais 900 caracteres (Task 2) — seria
vacuo, e foi CONSERTADO em vez de contornado.**
`index` acha a PRIMEIRA ocorrencia. Se a constante entrasse no `__all__` — como entram
`N_MINIMO_PARA_MEDIANA`, `N_MINIMO_PARA_MENOR` e `SERIES_NO_TOPO` —, a janela cairia no
bloco dos pisos de evidencia logo abaixo, que ja dizia "ESCOLHA" desde o 04-02, e o
criterio passaria com a constante muda. **Decisao:** manter o nome FORA do `__all__`, com a
razao escrita no proprio fonte. **Medido depois:** `index == rindex == 34615`, ou seja a
primeira ocorrencia E o sitio da definicao. O criterio literal agora mede o que diz medir.
Um discriminante por `rindex` ficou no teste de qualquer forma, porque a protecao depende
de alguem nao acrescentar o nome ao `__all__` no futuro.

**3. `test -z "$(git diff --stat -- config.toml)"` e os tres irmaos (verification 3 a 6) —
FRACOS por construcao.** Eles comparam o WORKING TREE com o `HEAD`, e com o trabalho
commitado eles saem com exit 0 mesmo que o arquivo tivesse sido alterado e commitado. O
proprio plano ja registrava a suspeita ("Os quatro REPROVAM sozinhos. A forma crua sai com
codigo 0 tendo mudado tudo"). *Discriminante acrescentado:*
`git diff --stat 77f8e58..HEAD -- <arquivos>` contra a **base do plano**, que cobre os seis
commits. Resultado: saida vazia para `config.toml`, `rastreador.py`, `visao.py`,
`__main__.py`, `requirements.txt`, `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py` e
`tests/test_bosses.py`. O `git diff --stat 77f8e58..HEAD` completo lista **exatamente os 5
arquivos do `files_modified`**.

## Contagem do pytest, com a base DESTE worktree

| Momento | Resultado |
|---|---|
| Base do worktree, antes de tocar em nada | **3005 passed, 23 skipped** |
| Depois dos tres tasks | **3077 passed, 23 skipped** |
| Delta | **+72 testes, 0 regressoes, contagem de skip inalterada** |

A arvore principal reporta **3026 passed, 2 skipped** — total coletado identico (3028). A
divergencia sao **21 testes que passam na main e sao PULADOS aqui**, e todos os 21 sao
pulos de isolamento de worktree, conferidos com `-rs`: `recordings/` (9 em
`test_mercado_replay`, 5 em `test_sugestao_de_calibracao`, 4 espalhados), `.venv/`
(`test_firewall_escopo`), `calibration.json` (`test_calibracao_mercado`) e as bindings
WinRT (`test_ocr`). Todos sao `gitignored` e nao se materializam num worktree — nenhum deles
tem relacao com este plano.

## Deviations from Plan

### Auto-fixed

**1. [Rule 1 - Bug] A afirmacao do controle negativo do fuzzy estava ERRADA**
- **Found during:** Task 2, ao rodar o teste RED
- **Issue:** o teste afirmava `similaridade("+3 Dragon Belt", "Dragon Belt") >= 0.8947`. Medido: **0,88**, abaixo do corte. Eu tinha escrito uma medicao que nunca medi.
- **Fix:** trocado pelos tres pares que realmente cruzam o corte (medidos: 0,9286 / 0,9375 / 0,9333), mais a assercao de que o par original fica abaixo — o que na verdade FORTALECE o argumento, porque mostra que o fuzzy erra de forma imprevisivel.
- **Commit:** `7038f6c`

**2. [Rule 1 - Bug] A advertencia do cabecalho saia numa linha de ~180 caracteres**
- **Found during:** Task 3, na inspecao visual da secao renderizada
- **Issue:** a advertencia rolava para fora da janela do console. Ela e a unica defesa contra o numero abaixo dela parecer acionavel; ilegivel, ela nao defende nada.
- **Fix:** `textwrap.wrap` em `LARGURA_DO_AVISO = 76` (stdlib, sem dependencia nova). O teste de "aparece exatamente uma vez" passou a contar sobre o texto ACHATADO, com controle negativo proprio (`* 2` conta 2, `"nada a ver"` conta 0).
- **Commit:** `57b80e7`

**3. [Rule 1 - Bug] As colunas dos componentes saiam escalonadas em relacao as do produto**
- **Found during:** Task 3, na mesma inspecao
- **Issue:** o recuo maior dos componentes empurrava nome, `menor`, `n` e idade duas colunas para a direita. Uma tabela desalinhada e uma tabela que nao cumpre a funcao de tabela.
- **Fix:** `COLUNA_DO_NOME = 16` e largura do rotulo derivada do recuo (`max(1, COLUNA_DO_NOME - len(recuo))`) — a hierarquia continua se lendo pelo recuo e as colunas caem no mesmo lugar.
- **Commit:** `57b80e7`

### Acrescimos alem do plano

**4. [Rule 2 - Correctness] `rende` e `quantidade` recusam FRACIONARIO**
- O plano exigia recusar booleano e nao positivo. Um `rende = 1.5` nao descreve craft nenhum e faria a margem depender de um arredondamento que ninguem escolheu. `1.0` cai junto, de proposito: aceitar o float redondo e recusar o quebrado seria uma regra que o usuario so descobre por tentativa.

**5. [Rule 2 - Correctness] `componentes` ausente ou vazio recusa**
- O plano exigia recusar `componentes` que nao e lista. Ausente ou vazio produziria uma "margem" igual ao proprio preco do produto — um numero grande, plausivel e sem significado, que e a familia de falha desta fase.

**6. [Rule 2 - Correctness] O PRODUTO concorre na disputa de "evidencia mais velha"**
- O plano falava de staleness por componente. Um produto com preco de uma semana atras estraga a conta exatamente como um ingrediente estragaria; promover so componentes esconderia metade dos casos.

## Threat Flags

Nenhuma superficie nova alem das ja registradas no `<threat_model>` do plano. Este plano nao
abre porta de rede, nao escreve arquivo nenhum em producao (a analise so LE o CSV) e nao
acrescenta dependencia. `difflib` e `textwrap` sao stdlib.

## Known Stubs

Nenhum.

## Conferencia humana ABERTA (do proprio plano)

Com pelo menos uma sessao de `--mercado` gravada, o usuario descomenta um `[[receita]]` de um
craft que ele conhece de verdade e confere que os numeros batem com o World Exchange, que a
staleness de cada componente e plausivel, e que um nome digitado errado quebra a margem com
uma mensagem que ajuda a corrigir. **E o unico jeito de fechar a limitacao numero 5:** o
programa nao conhece o crafting do jogo, e uma receita errada produz um numero perfeitamente
formatado e completamente falso.

> **Nota para o 04-05:** o bloco `[[receita]]` COMENTADO no `config.toml` continua por
> escrever — este plano entregou so o LEITOR, e `config.toml` esta conferido como intocado
> nos seis commits. O exemplo que o 04-05 deve escrever ja existe pronto no fonte, em
> `config._EXEMPLO_DA_RECEITA`, e a forma e a de TABELA INLINE.

## Self-Check: PASSED

- Os 5 arquivos de codigo e o proprio SUMMARY conferidos no disco.
- Os 6 commits conferidos no `git log` (`e643e1a`, `60b563d`, `7038f6c`, `8db0219`,
  `c0039cf`, `57b80e7`), todos sobre a base `77f8e58`.
- `git diff --stat 77f8e58..HEAD` lista exatamente os 5 arquivos do `files_modified` e
  nenhum outro.
- Nenhum `git commit --amend`. `calibration.json` e `.mercado/` intocados — a `.mercado/`
  nem existe neste worktree.
