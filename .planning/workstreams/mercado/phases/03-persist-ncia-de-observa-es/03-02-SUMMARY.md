---
phase: 03-persist-ncia-de-observa-es
plan: 02
subsystem: infra
tags: [montagem, factory, degradacao, logging, csv, google-sheets, gitignore, windows]

requires:
  - phase: 03-persist-ncia-de-observa-es
    provides: "`RegistroDeObservacoes`, `ContratoDoArquivoQuebrado` e `PASTA_DO_MERCADO` (03-01), com o construtor deliberadamente indefeso"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "`montar_gravador` — o padrao de montagem em cinco regras, e o `configurar_log` que entrega o aviso ao console E ao arquivo"
provides:
  - "`montar_registro_de_mercado(pasta=None)` em `l2scanner/__main__.py`: a porta de entrada que envolve o construtor inteiro, cobre os quatro modos de falha medidos mais os DOIS motivos do contrato quebrado, avisa alto em duas mensagens e devolve `None` sem nunca levantar"
  - "`ARQUIVO_DO_LEIAME`, `TEXTO_DO_LEIAME` e `escrever_leiame(pasta) -> bool` em `l2scanner/mercado_registro.py`: o LEIAME nasce com a pasta e NUNCA e reescrito"
  - "`.mercado/LEIAME.txt` — o roteiro de importacao no Sheets, os centesimos, a distincao entre residuo vazio e residuo zero, e o sinal de mais como pergunta em aberto"
  - "O comentario do `.gitignore` citando os DOIS arquivos e os dois donos, com a entrada `.mercado/` intacta"
affects: [03-03-portao-humano, fase-4-modo-mercado, DETC-02, ANAL-*]

actuals:
  tokens: 6481
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Montagem que envolve o construtor INTEIRO, com captura estreita de DOIS tipos nomeados e divergencia justificada no fonte"
    - "Documento write-once ao lado do dado: escreve so se ausente, nunca sobrescreve o que o usuario editou"
    - "Filtro por NOME DE LOGGER no teste quando duas camadas gritam sobre o mesmo evento"

key-files:
  created:
    - .planning/workstreams/mercado/phases/03-persist-ncia-de-observa-es/deferred-items.md
  modified:
    - l2scanner/__main__.py
    - l2scanner/mercado_registro.py
    - tests/test_mercado_registro.py
    - .gitignore

key-decisions:
  - "A captura da montagem e `(OSError, ContratoDoArquivoQuebrado)` — divergencia de UM TIPO com a regra 2 da casa, justificada por escrito na docstring: o contrato quebrado nao e falha de sistema de arquivos, mas o desfecho e o mesmo (feature desligada, scanner de pe), entao o tratamento e o mesmo. Continua estreita: dois tipos nomeados, nunca `except Exception`"
  - "O TIPO DE RETORNO NAO E ANOTADO, contra a letra do plano e a favor do vizinho: `montar_vigia_do_mercado` (logo acima) tambem nao anota, porque o tipo so existe atras do import ADIADO. Anotar deixaria no modulo um nome que `typing.get_type_hints` nao resolve, e o unico jeito de resolver seria um bloco `TYPE_CHECKING` no topo do `__main__.py` — arquivo disputado com outro workstream nesta wave"
  - "O arquivo de ZERO BYTES marcado somente-leitura e a forma escolhida para provar o `PermissionError` no arranque: e o unico arranque que PRECISA escrever (o cabecalho nasce ali). Com o arquivo cheio e valido o bit seria inerte, que e a mesma armadilha do `chmod` sobre pasta"
  - "O LEIAME e escrito sem acento, como todo texto que este projeto poe na frente do usuario. O arquivo e UTF-8; a escolha e de consistencia com os `log.error` que a mesma frase acompanha, nao de codificacao"
  - "O comentario do `.gitignore` foi mantido em EXATAMENTE quatro linhas para que a janela ancorada `grep -B4 '^\\.mercado/$'` alcance a palavra `observacoes` mesmo se outro workstream mexer no arquivo"

patterns-established:
  - "Divergencia de captura declarada no fonte: quando uma montagem precisa pegar um tipo que nao e `OSError`, o motivo e o desfecho identico vao escritos na docstring, e o teste prende a largura por AST"
  - "Documento write-once na pasta do usuario: `escrever(pasta) -> bool`, `True` escreveu / `False` ja existia, com a razao (a anotacao do usuario) no fonte"
  - "Quando duas camadas gritam sobre o mesmo evento, o teste filtra por `record.name` — sem isso o assert prova a mensagem da camada errada"

requirements-completed: [PERS-01, PERS-03]

coverage:
  - id: D1
    description: "A montagem envolve o construtor INTEIRO e sobrevive aos quatro modos de falha medidos no Windows — em especial o `mkdir` sobre nome ocupado por ARQUIVO (`FileExistsError`, errno 17), que roda fora de qualquer rede dentro do construtor"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemDoRegistroDeMercado::test_um_ARQUIVO_ocupando_o_nome_da_pasta_devolve_None"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemDoRegistroDeMercado::test_o_CSV_somente_leitura_no_arranque_que_PRECISA_escrever"
        status: pass
    human_judgment: false
  - id: D2
    description: "O `ContratoDoArquivoQuebrado` desliga a feature PELA MONTAGEM pelos dois motivos (cabecalho divergente, D-12; arquivo sem quebra de linha final, D-17) em vez de subir como traceback cru — e no caso do D-17 nenhum byte do arquivo do usuario e tocado"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemDoRegistroDeMercado::test_o_cabecalho_divergente_desliga_pela_MONTAGEM"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemDoRegistroDeMercado::test_o_arquivo_SEM_QUEBRA_FINAL_desliga_e_o_disco_fica_INTOCADO"
        status: pass
    human_judgment: false
  - id: D3
    description: "O aviso alto tem as DUAS mensagens em `log.error`, a segunda dizendo o que continua funcionando, e chega ao console E ao arquivo pelo `configurar_log` que o scanner ja instala (D-13)"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemDoRegistroDeMercado::test_a_SEGUNDA_mensagem_diz_o_que_CONTINUA_funcionando"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOAvisoALTO_CHEGA_AO_CONSOLE::test_configurar_log_instala_console_sobre_stdout_e_arquivo_rotativo"
        status: pass
    human_judgment: false
  - id: D4
    description: "A montagem NUNCA levanta e a captura e estreita — conferido por AST, que um comentario nao invalida nem satisfaz"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemNUNCA_LEVANTA::test_nao_ha_raise_em_lugar_nenhum_da_montagem"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestAMontagemNUNCA_LEVANTA::test_a_captura_e_ESTREITA_e_os_dois_tipos_sao_NOMEADOS"
        status: pass
    human_judgment: false
  - id: D5
    description: "O LEIAME nasce com a pasta, nunca e reescrito, e um arquivo editado a mao sobrevive byte a byte ao proximo arranque"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOLeiameNasceComAPastaEnUNCA_E_REESCRITO"
        status: pass
    human_judgment: false
  - id: D6
    description: "O texto do LEIAME responde sozinho as quatro perguntas: o separador PERSONALIZADO com `\";\"`, os centesimos com `6200`/`62,00`, a celula vazia contra o zero no residuo, e o sinal de mais como pergunta em aberto"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_mercado_registro.py::TestOTextoDoLeiameRESPONDE_SOZINHO"
        status: pass
    human_judgment: false
  - id: D7
    description: "A importacao REAL no Google Sheets, com o roteiro do LEIAME na mao: as colunas nao colapsam, `6200` fica legivel, e uma linha cujo nome comeca com `+` cai como TEXTO e nao como `#ERROR!`"
    requirement: "PERS-01"
    verification: []
    human_judgment: true
    rationale: "O criterio 2 da fase exige importacao REAL, nao presumida, e o comportamento do Sheets diante de uma celula iniciada em `+` e a suposicao A3 da pesquisa — declarada ALTA e NAO MEDIDA. Nenhum teste desta arvore pode afirma-la; e o portao humano do 03-03."

duration: 18min
completed: 2026-08-31
status: complete
---

# Phase 03 Plan 02: A montagem e o LEIAME Summary

**O registro de observacoes ganhou a porta de entrada que a casa exige — uma montagem que envolve o construtor indefeso inteiro, cobre os quatro modos de falha medidos MAIS os dois motivos do contrato quebrado, avisa alto em duas mensagens e devolve `None` sem nunca levantar — e a pasta `.mercado/` passou a nascer com um LEIAME que ensina sozinho a importacao no Sheets.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-31T03:58:00Z
- **Completed:** 2026-08-31T04:16:00Z
- **Tasks:** 2 (as duas TDD: RED -> GREEN)
- **Files modified:** 4 (mais 1 criado, o `deferred-items.md`)

## Accomplishments

- **`montar_registro_de_mercado` existe, ao lado de `montar_vigia_do_mercado`, e o diff no `__main__.py` e um ACRESCIMO PURO:** 78 linhas inseridas depois da linha 465, zero linhas removidas, zero linhas movidas. Nenhuma das regioes que o workstream `tiat` declara (108, 342-366, 1644-1660, 1745-1760, 2160-2216) foi tocada.
- **As cinco regras do padrao da casa estao cobertas uma a uma, e cada uma tem teste.** O `try` sobre o construtor INTEIRO tem o teste do nome-ocupado-por-arquivo, que e o `mkdir` levantando `FileExistsError` fora de qualquer rede; a captura estreita e o `return None` estao presos por AST; as duas mensagens e a frase do PERS-03 estao presas por substring; o `error` contra `warning` esta preso pela contagem exata de dois registros.
- **A divergencia aprovada esta implementada E justificada no fonte.** `ContratoDoArquivoQuebrado` e capturado ao lado do `OSError`, com os DOIS motivos nomeados na docstring (D-12 cabecalho, D-17 terminador). Sem ela a excecao subiria do arranque como traceback cru — o modo de falha exato que a montagem existe para consertar.
- **A metade do D-13 que o `caplog` nao ve agora esta presa por teste.** `caplog` prova que o `log.error` saiu; ele nao prova que o usuario le. O teste novo afirma que `configurar_log` instala um `StreamHandler` sobre `sys.stdout` alem do `RotatingFileHandler` — e ele nasceu VERDE, que era o esperado: a propriedade ja existia, o que faltava era alguem a afirmar.
- **O LEIAME responde sozinho as quatro perguntas** que o usuario faria seis meses depois, incluindo a que ele nem sabe que tem: **nao existe preset de ponto e virgula no dialogo do Sheets**, e quem procurar um vai procurar por uma opcao que nao existe.
- **Nenhuma dependencia nova, nenhum arquivo de tiat/bosses/agenda tocado, e nenhuma entrada nova no `.gitignore`.**

## Task Commits

1. **Task 1 (TDD): `montar_registro_de_mercado`** — `1a3431f` (test, RED) -> `d2e3994` (feat, GREEN)
2. **Task 2 (TDD): o LEIAME e o comentario do `.gitignore`** — `9109c50` (test, RED) -> `3dbe8ea` (feat, GREEN)

Nenhum passo de REFACTOR: as duas implementacoes nasceram na forma final.

## O diff exato do `__main__.py`

```
@@ -465,6 +465,84 @@ def montar_vigia_do_mercado(cal: Calibracao, na_janela: bool):
 1 file changed, 78 insertions(+), 0 deletions(-)
```

- **Uma unica regiao:** logo depois de `montar_vigia_do_mercado` (que termina na linha 465) e antes de `_duracao_legivel`.
- **A funcao nova ocupa as linhas 468-543.** `_duracao_legivel`, que era 468, passou a ser 546.
- **Zero remocoes.** Nada foi reordenado, nenhum import mudou, o topo do arquivo (onde mora a linha 108 que o `tiat` edita) nao foi tocado.
- **Um unico import, e ele e ADIADO para dentro da funcao**, no precedente do vizinho: `from .mercado_registro import (ARQUIVO_DE_OBSERVACOES, PASTA_DO_MERCADO, ContratoDoArquivoQuebrado, RegistroDeObservacoes)`.

Consequencia para o merge: as unicas linhas do `__main__.py` que este plano toca ficam em 466-467 (as duas linhas em branco existentes viram o contexto do hunk) e num bloco novo. Um `tiat` que edite 108, 342-366, 1644-1660, 1745-1760 e 2160-2216 nao colide — o unico efeito e o deslocamento de +78 nas linhas posteriores a 465.

## Files Created/Modified

- `l2scanner/__main__.py` — +78 linhas: `montar_registro_de_mercado`, so isso.
- `l2scanner/mercado_registro.py` — +122 linhas: `ARQUIVO_DO_LEIAME`, `TEXTO_DO_LEIAME`, `escrever_leiame`, a chamada no construtor logo depois do `mkdir`, e os dois nomes novos no `__all__`.
- `tests/test_mercado_registro.py` — +375 linhas: 19 testes novos em cinco classes (a montagem, o AST, o console, o LEIAME que nasce, o texto do LEIAME).
- `.gitignore` — 4 linhas de COMENTARIO reescritas. A entrada `.mercado/` nao mudou e nenhuma entrada nova entrou.
- `.planning/.../deferred-items.md` (NOVO) — o teste vermelho da Fase 2 encontrado na verificacao, com o motivo de nao ter sido consertado aqui.

## Decisions Made

### 1. O tipo de retorno da montagem NAO foi anotado — e isso contraria a letra do plano

O plano escreve a assinatura como `montar_registro_de_mercado(pasta: Path | None = None) -> RegistroDeObservacoes | None`. Ficou sem a anotacao de retorno, e o motivo e o vizinho imediato: `montar_vigia_do_mercado` — que o proprio plano manda ler como "a vizinhanca onde a funcao nova vai morar, e o precedente do import ADIADO" — tambem nao anota o retorno, pela mesma razao. O tipo so existe atras do import adiado, entao anota-lo deixaria no modulo um nome que `typing.get_type_hints` nao resolve.

As tres saidas foram pesadas:

- **Anotar assim mesmo.** Funciona em tempo de execucao (`from __future__ import annotations` na linha 8 torna a anotacao preguicosa) e nenhum linter roda neste repositorio — nao ha `pyproject.toml`, `ruff.toml`, `setup.cfg` nem teste de lint. Mas deixa uma armadilha silenciosa para quem um dia chamar `get_type_hints`.
- **Importar sob `TYPE_CHECKING`.** Exigiria um bloco novo no TOPO do `__main__.py`, que e exatamente a regiao disputada com o workstream `tiat` nesta wave, e deslocaria as linhas que ele edita. Custo de merge desproporcional a um beneficio de documentacao.
- **Nao anotar, e dizer o tipo na primeira linha da docstring** ("Devolve um `RegistroDeObservacoes` ou `None`, e NUNCA levanta"). Escolhida: mesmo valor documental, zero nome pendurado, zero linha no topo do arquivo.

Nenhum criterio de aceitacao do plano cobrava a anotacao de retorno — o que ele cobra (`parameters['pasta'].default is None`) esta verde.

### 2. O `PermissionError` do arranque foi provado com um arquivo de ZERO BYTES

O plano pede um teste "com o CSV marcado somente-leitura e um arranque que precisa escrever o cabecalho". Esse arranque tem um estado so: **arquivo de zero bytes**. Com o CSV cheio e valido, `carregar()` abre em `"r"` e o bit de somente-leitura nao tem o que impedir — o teste passaria por acidente, que e a mesma armadilha do `chmod` sobre pasta que a pesquisa mediu. Com zero bytes o modulo cai em `_criar_com_cabecalho`, que abre em `"w"`, e ai o `PermissionError` (errno 13) nasce de verdade. A razao esta na docstring do teste.

### 3. Os testes filtram os `ERROR` por NOME DE LOGGER

Nos dois casos de contrato quebrado hoje gritam DUAS camadas: o modulo de registro (`l2scanner.mercado_registro`, com as hipoteses e a instrucao de conserto que o 03-01 escreveu) e a montagem (`l2scanner`, com as duas mensagens da casa). Sem filtrar por `record.name`, o assert de `A_PROMESSA` seria satisfeito pela mensagem do 03-01 — a frase "morte, saida e ressurreicao" aparece nas duas — e o teste provaria a camada errada. O filtro esta num helper com o motivo escrito, e `__main__.py:152` nomeia o logger `"l2scanner"` e nao `__name__`, o que tambem foi anotado ali.

### 4. O comentario do `.gitignore` ficou com exatamente quatro linhas

O criterio de aceitacao usa uma janela ancorada na ENTRADA (`grep -B4 '^\.mercado/$'`), de proposito, para nao depender de numeros de linha que deslizam se outro workstream mexer no arquivo. Quatro linhas de comentario e o unico tamanho em que a palavra `observacoes` cai dentro da janela com folga. O comentario original tinha quatro linhas e perdeu um pedaco da prosa final ("e nenhuma das duas saberia dizer qual metade e sua") para caber os dois arquivos e os dois donos; o motivo do ignore continua escrito.

## Deviations from Plan

### Auto-fixed Issues

Nenhum. Nenhum bug, nenhuma funcionalidade critica ausente e nenhum bloqueio apareceu durante as duas tasks — as duas implementacoes passaram na primeira execucao depois do RED.

### Divergencias de forma, todas declaradas

**1. [Decisao - Forma] O tipo de retorno da montagem nao foi anotado**

- **Onde:** Task 1, `l2scanner/__main__.py:468`
- **O plano dizia:** `-> RegistroDeObservacoes | None`
- **O que ficou:** sem anotacao de retorno, com o tipo declarado na primeira linha da docstring e o motivo escrito logo abaixo
- **Motivo:** precedente do vizinho imediato (`montar_vigia_do_mercado`) mais o custo de merge de tocar o topo de um arquivo disputado. Detalhado em "Decisions Made #1".
- **Impacto no criterio:** nenhum. O unico criterio sobre a assinatura (`parameters['pasta'].default is None`) esta verde.

---

**Total deviations:** 0 auto-fix, 1 divergencia de forma declarada.
**Impact on plan:** nenhum sobre o escopo, o comportamento ou os criterios. Todos os criterios de aceitacao das duas tasks estao verdes.

## Issues Encountered

### Um teste da Fase 2 esta VERMELHO na base, e nao e deste plano

`tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida` falha na suite completa **e falha em isolamento**, com quatro avisos `linha N RECUSADA (numero): a coluna Total nao se leu inteira`.

**Nao foi consertado, e a regra de escopo e clara:** so se conserta o que a propria task quebrou. A prova de que nao e desta task e estrutural e curta — o 03-02 alterou quatro arquivos e **nenhum deles aparece no grafo de import** de `tests/test_mercado_leitura.py`:

```
grep -n "__main__\|mercado_registro" tests/test_mercado_leitura.py \
    l2scanner/mercado_leitura.py l2scanner/mercado_pagina.py \
    l2scanner/mercado_visao.py tests/conftest.py    ->  zero linhas
```

Python nao e afetado por arquivo que nunca importa, e o teste falha em processo limpo, sem nenhum teste do 03-02 coletado.

**A discrepancia que fica aberta e o achado de verdade:** a wave 1 mediu, no commit-base `0820587`, **2754 passed, 23 skipped, zero failed**. Nesta arvore, no commit-base `f03eee80` — que ja inclui a wave 1 — a mesma suite da **1 failed**. Ou alguma coisa entre os dois commits quebrou o teste, ou a medicao da wave 1 nao alcancou este arquivo. Registrado com os dois primeiros passos de investigacao em `deferred-items.md`.

**A aritmetica fecha e confirma que nada mais mudou:** 2772 passed + 1 failed = 2773 = 2754 da baseline + 19 testes novos deste plano. Nenhum outro teste mudou de cor.

### O flake conhecido nao apareceu

`tests/test_agenda.py`: **145 passed**, sessao completa, sem o `KeyboardInterrupt` de `:1141`.

## Suite

| Alvo | Resultado |
|---|---|
| `tests/test_mercado_registro.py` | **114 passed** (95 do 03-01 + 19 novos) |
| `tests/test_gravador_honesto.py` + `test_mercado_catalogo.py` + `test_mercado_27x.py` + `test_firewall_escopo.py` | **137 passed, 2 skipped** — os analogs de montagem e de arquivo continuam intocados, e o firewall do FIRE-01 continua verde |
| Suite completa, sem `test_agenda.py` | **2772 passed, 1 failed, 23 skipped** — o failed e o da Fase 2 descrito acima, vermelho tambem na base |
| `tests/test_agenda.py` | **145 passed**, sem o flake |

Escopo conferido: `git diff --name-only` sobre os quatro commits lista `.gitignore`, `l2scanner/__main__.py`, `l2scanner/mercado_registro.py` e `tests/test_mercado_registro.py`. **`l2scanner/rastreador.py` e `l2scanner/visao.py` NAO aparecem.** `git status --short` nao lista `calibration.json`.

## User Setup Required

Nenhum. Zero dependencia nova, zero segredo, zero configuracao. O `.mercado/LEIAME.txt` nasce sozinho no primeiro arranque e ja esta coberto pelo mesmo ignore de diretorio que cobre o CSV.

## Next Phase Readiness

**Pronto para o 03-03 (portao humano).** O roteiro do dialogo do Sheets nao precisa ser redigido de novo no plano do portao: ele ja esta no `LEIAME.txt` que o usuario vai ter na pasta, na ordem em que ele vai executar. O item que o portao PRECISA carregar e o unico que nenhum teste desta arvore pode afirmar: **uma linha cujo nome comeca com `+` cai como texto ou como `#ERROR!` no Sheets?** O `+6 Agathion Alpha Hunter Sealed` esta no fixture versionado, com 15 nomes assim, e o proprio LEIAME ja avisa o usuario de que a resposta esperada e "avise", nao "conserte".

**Pronto para a Fase 4 (DETC-02).** `montar_registro_de_mercado` esta no trilho e **sem chamador, de proposito**. Quem ligar o modo `--mercado` chama a montagem, trata `None` como feature desligada, e nao precisa de nenhum `try` no ponto de ligacao — a rede ja esta do lado de dentro.

**O que a Fase 4 herda como divida honesta:** o PERS-03 continua verdadeiro por AUSENCIA DE ACOPLAMENTO, e nao por um teste de ponta a ponta com o mercado ligado ao lado do detector de morte. A montagem fecha a metade estrutural (nunca levanta, avisa alto, devolve `None`); a metade de ponta a ponta so existe quando houver chamador.

**Bloqueio para o `/gsd-ship`:** o teste vermelho da Fase 2 em `deferred-items.md`. Ele nao bloqueia o 03-03, mas nao deve atravessar o fechamento da fase sem datacao.

## Self-Check: PASSED

**Arquivos afirmados, conferidos em disco:**
- `l2scanner/__main__.py` — FOUND, `montar_registro_de_mercado` na linha 468
- `l2scanner/mercado_registro.py` — FOUND, `ARQUIVO_DO_LEIAME` e `escrever_leiame` importaveis (`python -c "... print('leiame ok')"` imprime `leiame ok`)
- `tests/test_mercado_registro.py` — FOUND, 114 testes
- `.gitignore` — FOUND, `grep -v '^#' | grep -c '^\.mercado/$'` devolve `1`, e `grep -B4 '^\.mercado/$' | grep -c 'observa'` devolve `1`
- `.planning/workstreams/mercado/phases/03-persist-ncia-de-observa-es/deferred-items.md` — FOUND

**Commits afirmados, conferidos no `git log`:** `1a3431f`, `d2e3994`, `9109c50`, `3dbe8ea` — os quatro presentes, na ordem RED/GREEN de cada task.

**Criterios de linha de comando do plano, executados:**
- `python -c "... assert callable(p.montar_registro_de_mercado); ... print('montagem ok')"` -> `montagem ok`
- `python -c "... assert not [n for n in ast.walk(a) if isinstance(n,ast.Raise)]; print('nunca levanta')"` -> `nunca levanta`
- `python -c "... assert m.ARQUIVO_DO_LEIAME == 'LEIAME.txt'; ... print('leiame ok')"` -> `leiame ok`
- `grep -v '^#' .gitignore | grep -c '^\.mercado/$'` -> `1`
- `grep -B4 '^\.mercado/$' .gitignore | grep -c 'observa'` -> `1`

**Nenhum stub:** varredura por `TODO`/`FIXME`/`placeholder`/`XXX`/`HACK` nos arquivos deste plano devolveu **uma unica ocorrencia, e ela e falso positivo**: a palavra portuguesa `TODOS` numa docstring de prosa em `tests/test_mercado_registro.py:1133`, escrita pelo 03-01. Nenhum valor vazio cabeado, nenhum componente sem fonte de dado. Nao ha secao `Known Stubs`.

---
*Phase: 03-persist-ncia-de-observa-es*
*Completed: 2026-08-31*
