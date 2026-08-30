---
phase: 01-reconhecimento-preciso-e-lista-de-bosses-no-config
workstream: tiat
plan: 03
subsystem: deteccao
tags: [regex, ocr, config-toml, debounce, ast-gate, seguranca]

requires:
  - phase: 01-01
    provides: "l2scanner/bosses.py (VigiaDeBosses, padrao_do_anuncio, _FOLGA_DE_OCR, _DIGITO_COM_FOLGA), l2scanner/config.py (ler_bosses), os dois [[boss]] no config.toml"
provides:
  - "tests/test_bosses.py — 84 testes: a matriz completa dos 8 criterios da fase, nos dois sentidos"
  - "l2scanner/bosses.py — VigiaDeBosses._bosses_identificados_no_alvo (a regra de desempate do quadro de alvo)"
  - "tests/test_presenca.py — bosses.py dentro de TestSemRelogioProprio.MODULOS"
affects: [01-04, "Fase 2 (janela de respawn)"]

actuals:
  tokens: 6620
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Desempate por SPAN no recorte sem frase: dois padroes casando trechos sobrepostos produzem silencio, nao escolha"
    - "Criterio afirmado como EQUIVALENCIA (a frase torta e a limpa produzem o mesmo aviso), e nao como 'a torta dispara'"
    - "Falso positivo de campo escrito como teste ANTES de ser um problema, para que a rejeicao por coincidencia vire garantia"
    - "Portao AST adotado por um modulo ANTES de ele ganhar logica de tempo"

key-files:
  created: []
  modified:
    - tests/test_bosses.py
    - l2scanner/bosses.py
    - tests/test_presenca.py

key-decisions:
  - "Empate no quadro de alvo (dois [[boss]] casando trechos sobrepostos) resolve para SILENCIO, nao para a ordem do config"
  - "O desempate e SO do caminho do alvo; o chat tem [Lv. NN] has spawned provando a origem e nao precisa dele"
  - "A notificacao de mercado ('added on the market [15,54 XM Coin]') entra na matriz como caso negativo permanente"
  - "bosses.py entra no portao AST de relogio na Fase 1, antes de ter logica de tempo"
  - "config.py NAO foi alterado: a matriz de configuracao inteira passou de primeira"

requirements-completed: [RECO-01, RECO-02, RECO-03, RECO-04, RECO-05, VIGI-01, VIGI-02, VIGI-03, VIGI-04]

duration: 41min
completed: 2026-08-30
status: complete
---

# Phase 1 Plan 03: A matriz que torna os oito criterios verdadeiros — Summary

**Os oito criterios da fase deixaram de ser plausiveis e passaram a ser medidos: 30 asserções novas, o falso positivo REAL do chat (a notificação de mercado) escrito antes de virar problema, o único defeito que a matriz encontrou corrigido em `bosses.py`, e `bosses.py` dentro do portão AST de relógio com a mordida provada por mutação.**

## Performance

- **Duration:** ~41 min
- **Tasks:** 3 de 3
- **Suite:** 2197 passed / 14 skipped (baseline deste worktree) → **2227 passed / 14 skipped**. Zero testes existentes editados; zero enfraquecidos.
- **Arquivos:** 3 modificados, 0 criados, 0 apagados.

## Task Commits

| # | Tarefa | Commit | Tipo |
|---|--------|--------|------|
| 1 | RED — a matriz de reconhecimento, com o falso positivo real do mercado | `eec913f` | test |
| 1 | GREEN — o empate no quadro de alvo vira silencio | `b2a4573` | feat |
| 2 | A matriz de configuracao — VIGI-01 fechado do arquivo ate a mensagem | `53f6301` | test |
| 3 | `bosses.py` entra no portao AST de relogio | `acf9cf1` | test |

## 1. Quais casos da matriz FALHARAM na primeira rodada (OBRIGATORIO — alimenta 01-04)

**Dos 30 casos novos, exatamente DOIS falharam.** Os dois eram o mesmo defeito, e os dois eram do caminho do ALVO.

| Caso | Resultado observado | Correcao |
|---|---|---|
| `TestOCaminhoDoAlvo::test_dois_bosses_casando_o_mesmo_trecho_do_alvo_nao_produzem_aviso` — roster `("Tiat", "Tiat North")`, alvo lendo `Tiat North` | **DOIS avisos**, um por boss — e um deles e comprovadamente falso, porque um alvo e um mob so | `VigiaDeBosses._bosses_identificados_no_alvo` em `l2scanner/bosses.py` |
| `TestOCaminhoDoAlvo::test_o_empate_no_alvo_nao_apaga_o_anuncio_do_chat` — o mesmo roster, com o anuncio de `Tiat North` tambem no chat | Aviso de `Tiat` pela origem ALVO + `Tiat North` como `CHAT_E_ALVO` | a mesma funcao, aplicada SO ao caminho do alvo |

**O que a matriz NAO encontrou, e o dado importa tanto quanto o defeito:**

- **`l2scanner/config.py` nao precisou de uma linha.** Os nove casos de bloco torto, os dois de nome vazio, as duplicatas por caixa, a lista vazia, o arquivo ausente e o TOML malformado passaram todos de primeira, com as mensagens ja citando o boss e o campo. A validacao que `01-01` escreveu espelhando `_evento_de_dict` estava completa.
- **O nivel com LETRA O ja passava.** `_DIGITO_COM_FOLGA` nao precisou de ampliacao — a classe que `01-01` mediu ja cobria `O`, `l`, `S`, `B`, `g`, `A`.
- **O casamento linha a linha ja existia.** `splitlines()` estava implementado, e o teste de costura ja estava escrito.
- **O nome vindo do config para a mensagem ja estava certo.** O caso hostil novo (comando + endereco cercando o anuncio) passou de primeira.
- **O alvo lendo `Tiat` truncado com `North`/`South` na lista ja produzia zero avisos** — nao por desempate, mas porque `padrao_do_nome` exige o nome COMPLETO. O plano previa que este caso poderia falhar produzindo dois avisos; ele nao falhou. O empate real e outro, e esta na tabela acima.

**Onde o padrao estava fragil, para o 01-04:** o unico ponto fragil medido nesta rodada e o **recorte do ALVO**, e a razao e estrutural — ali nao existe `[Lv. NN] has spawned` provando que o texto veio do servidor, entao toda a identificacao repousa no nome. O `01-04`, que confronta a frase real contra pixels, deve medir o recorte do alvo com a mesma seriedade do chat: um OCR que trunque ou emende o nome do alvo nao tem nenhuma outra evidencia para ser corrigido.

## 2. A regra final de desempate no quadro de alvo (OBRIGATORIO)

**Dois `[[boss]]` cujos padroes casam trechos que se SOBREPOEM no mesmo texto de alvo nao identificam nenhum dos dois. O aviso pela origem `ALVO` nao sai.**

Tres precisoes que a implementacao carrega e que a Fase 2 nao pode perder:

1. **A sobreposicao e medida por SPAN, e nao por presenca.** Dois bosses de nomes diferentes que aparecem em pontos diferentes do mesmo texto nao estao em empate — apenas estao ambos ali, e cada um e sinalizado normalmente. O empate e `outro != nome and outro_inicio < fim and inicio < outro_fim`.
2. **O desempate e exclusivo do caminho do ALVO.** A linha do chat traz `[Lv. NN] has spawned` provando a origem: nao ha ambiguidade a resolver ali. Apagar um anuncio do chat por causa de um empate NOUTRO recorte trocaria um falso positivo barato por um falso negativo silencioso, que e o erro caro (R-02). Ha um teste dedicado a essa fronteira.
3. **As tres saidas possiveis foram pesadas, e a escolha esta escrita no codigo.** Avisar os dois → metade dos avisos manda a party para o lugar errado. Escolher pela ordem do config → um chute com cara de certeza, invisivel para o usuario. Nao avisar → perde-se um alerta que o chat, se o boss realmente nasceu, entrega pelo caminho proprio dele. **Na Fase 2 a conta fica pior e e ela que trava a decisao:** este mesmo sinal vira ancora de uma contagem de 6 a 8 horas gravada em disco, e uma ancora chutada produz horas depois uma previsao errada que a party nao tem como distinguir de uma certa.

## 3. T-03-05 reafirmado, com a nota de que a Fase 2 o herda com severidade MAIOR (OBRIGATORIO)

**Um jogador digitando a frase exata do anuncio (`Tiat North [Lv. 60] has spawned!`) dispara o alerta. Continua `accept`, e continua deliberado.**

A unica defesa possivel seria ancorar o reconhecimento em algo que o jogador nao controla — a cor de sistema da linha — e o CONTEXT difere isso ate um falso positivo real aparecer em campo. A matriz **nao tenta** fechar este vetor, e nao tentar e a decisao.

**Na Fase 2 a severidade sobe de `medium` para `high`, e a reavaliacao e obrigatoria antes de a ancora duravel existir.** Hoje o custo do spoofing e uma mensagem inutil que a party descarta em dez segundos. Na Fase 2 o custo e uma ancora falsa gravada em `.agenda/`, que produz um aviso de "a janela abriu" seis horas depois para um nascimento que nunca aconteceu — e a party se desloca. **Uma previsao ancorada em ruido e estritamente pior do que nao ter previsao nenhuma.**

**A alavanca continua disponivel e agora esta MEDIDA:** a linha do anuncio sai em **verde** (cor de sistema), medida dos prints do usuario em 2026-08-30. A notificacao de mercado — o outro falso positivo plausivel — sai em laranja/dourado. As duas cores sao distintas entre si e distintas do texto dos jogadores, entao o filtro por cor e viavel quando a Fase 2 precisar dele.

## 4. O falso positivo REAL, e por que ele entrou na matriz

O coordenador entregou, no meio da execucao, evidencia nova medida dos prints do usuario. O caso mais perigoso do arquivo **nao e** o jogador digitando "tiat":

```
-> Dragon Belt - 1 pcs: added on the market [15,54 XM Coin]
```

E uma linha de **sistema** do mesmo chat, com o **mesmo icone de sino** do anuncio de boss, com **colchetes** e com **numero dentro dos colchetes**. Ela compartilha a estrutura visual do anuncio verdadeiro, o que a torna muito mais plausivel como falso positivo do que qualquer coisa digitada — e faz com que um humano lendo a regex nao perceba que ela quase casa.

**O padrao atual a rejeita porque falta `has spawned`. Isso era COINCIDENCIA; escrita como teste, virou garantia.** Qualquer afrouxamento futuro da parte fixa passaria a aceita-la, e o grupo de WhatsApp receberia um aviso de boss toda vez que alguem vendesse um item. Ela mora no mesmo arquivo onde moram os dois sentidos do trade-off, ao lado do caso positivo degradado — que e exatamente o ponto: quem afrouxar para salvar o positivo ve o negativo quebrar no mesmo `pytest`.

Caso secundario do mesmo print, mais fraco e de graca: `Christine : PROCURO PT EM PLAINS ARCHER LVL 62 127GS` — jogador, com `LVL 62`, que exercita a folga aberta pelos colchetes opcionais.

**Correcao de fato herdada:** a cor do anuncio e **verde**, e nao laranja como registros anteriores diziam. Nenhuma docstring deste plano escreve "laranja"; `grep -rn laranja l2scanner/ tests/ config.toml` nao devolve nada.

## Verificacao dos guardas — os dois provados por MUTACAO

Um portao que nunca foi visto ficar vermelho e uma politica, nao uma estrutura. Os dois desta fase foram mutados, observados vermelhos e revertidos.

| Guarda | Mutacao aplicada | Resultado | Estado |
|---|---|---|---|
| `TestONomeDoConfigNaoViraCuringa` (T-01-03) | `re.escape(caractere)` → `caractere` no ramo final de `_com_folga_de_ocr` | **5 testes vermelhos**, os dois novos (`Tiat(` e `Tiat[a-z]`) inclusive, mais `FutureWarning: Possible nested set` | revertido, verde |
| `TestSemRelogioProprio` (portao AST) | `_mutacao = datetime.now()` dentro de `VigiaDeBosses.avaliar` | **vermelho nomeando o modulo**: `bosses.py tem relogio proprio: ['datetime.now']` | revertido, verde |

## O `\d+` continua PROIBIDO, e a proibicao esta medida

`grep -n 'd+' l2scanner/bosses.py` devolve duas linhas, **as duas dentro do comentario que explica por que a sequencia nao e usada**. O caso `T1a7 Nor7h [Lv. 8O] has spawned!` — onde o segundo caractere do nivel e a LETRA O — passa, e passa afirmado como **equivalencia**: mesmo boss, mesmo texto, mesma origem que a frase limpa. Um teste que so afirmasse "a torta dispara" continuaria verde se ela disparasse nomeando o boss errado.

## Os 8 criterios do ROADMAP, e onde cada um e afirmado

| # | Criterio | Onde |
|---|---|---|
| 1 | Chat digitado nao dispara; a frase do servidor dispara e nomeia North/South | `TestOAnuncioDoServidorContraOChatDigitado` (12 testes), `TestAIdentidadeVemDoConfig` |
| 2 | Chat mudo + alvo `Tiat South` → aviso pelo alvo, caminho proprio | `TestOCaminhoDoAlvo` (5 testes) |
| 3 | A frase degradada produz o MESMO alerta; os dois sentidos no mesmo arquivo | `TestAFraseTortaEAFraseLimpaProduzemOMesmoAviso` (7 casos) + `TestOAnuncioDoServidorContraOChatDigitado`, no mesmo arquivo, de proposito |
| 4 | Mesmo boss nos dois sinais → UM aviso; bosses diferentes → DOIS | `TestORearmeEPorBoss` (4 testes), incluindo o terceiro tick com o anuncio persistindo |
| 5 | Um `[[boss]]` novo passa a ser vigiado sem tocar em `.py` | `TestUmBossInventadoPassaAVigiadoSemTocarEmPy` (4 testes) |
| 6 | Bloco torto derruba o arranque citando boss e campo | `TestARecusaCitaOBossEOCampo` (11 testes) |
| 7 | Sem `[[boss]]` o scanner sobe; arquivo ausente nao e erro | `TestLerBosses`, `TestOArranque` |
| 8 | `calibrar-tiat.bat` nao nomeia mob (OPER-01) | **do plano 01-02**, nao deste |

## Deviations from Plan

### 1. [Sem desvio de asseracao] A Task 2 nao teve fase RED

- **Encontrado durante:** Task 2
- **Situacao:** o plano marca a tarefa como `tdd="true"` esperando que a matriz de configuracao apontasse defeito em `config.py` (a recusa de duplicata, entre outros). **Os 17 casos passaram de primeira** — `01-01` ja tinha escrito a validacao inteira, duplicata por caixa inclusive.
- **Decisao:** a tarefa virou um commit `test(...)` unico em vez de RED+GREEN. Nenhuma asseracao foi enfraquecida para produzir esse resultado; o commit registra por escrito que zero correcao foi necessaria, e a mitigacao de T-01-03 foi provada por mutacao para que a passagem de primeira nao fosse confundida com prova vazia.

### 2. [Rule 2 - correcao de seguranca] O desempate do quadro de alvo

- **Encontrado durante:** Task 1
- **Problema:** dois `[[boss]]` casando trechos sobrepostos no mesmo texto de alvo produziam um aviso para cada, e no maximo um pode ser verdade.
- **Solucao:** `VigiaDeBosses._bosses_identificados_no_alvo`, com a razao (incluindo o agravamento na Fase 2) escrita na docstring da funcao e um paragrafo novo na docstring de modulo.
- **Commit:** `b2a4573`

### 3. [Evidencia nova durante a execucao] Os dois casos negativos dos prints

- **Encontrado durante:** Task 1, por mensagem do coordenador
- **Acao:** `test_a_notificacao_de_mercado_nao_e_confundida_com_o_anuncio` e `test_um_nivel_digitado_por_jogador_sem_colchetes_nao_dispara` entraram na matriz, com a razao ("hoje e coincidencia; escrita, e garantia") na docstring. Nenhuma docstring escreve "laranja".

---

**Total de desvios:** 3. **Nenhum enfraquece asseracao, nenhum expande escopo.**

## Known Stubs

Nenhum. Nao ha valor codificado que chegue a UI, nem componente sem fonte de dados, nem `TODO`/`FIXME` introduzido por este plano.

## Threat Flags

Nenhuma superficie nova. As mitigacoes do registro deste plano estao todas implementadas E provadas:

| Ameaca | Estado |
|---|---|
| T-03-01 (metacaractere no `nome`) | `mitigate` — 3 casos novos, mitigacao provada por mutacao |
| T-03-02 (texto do OCR vazando para o grupo) | `mitigate` — caso hostil com comando e endereco |
| T-03-03 (costura de duas linhas) | `mitigate` — ja existia de `01-01`, preservado |
| T-03-04 (falso negativo silencioso por aperto futuro) | `mitigate` — os dois sentidos no mesmo arquivo, mais o falso positivo real do mercado |
| T-03-05 (jogador digitando a frase exata) | `accept` — **herdado pela Fase 2 com severidade MAIOR**, ver secao 3 |
| T-03-06 (portao que para de guardar) | `mitigate` — mordida provada por mutacao |
| T-03-SC (instalacao de pacotes) | `accept` — nenhuma dependencia nova, nenhum gerenciador executado |

## Verification

| Comando | Resultado |
|---|---|
| `python -m pytest tests/ -q` | **2227 passed, 14 skipped** (baseline 2197 / 14) |
| `python -m pytest tests/test_bosses.py -q` | 84 passed (eram 55) |
| `python -m pytest tests/test_agenda.py -q` | verde — a seccao de boss do `config.toml` nao moveu o corte do guarda de cabecalho |
| `python -m pytest tests/test_presenca.py -q` | 142 passed |
| `python -m pytest tests/test_presenca.py -q -k SemRelogioProprio` | 5 passed (4 modulos + prova-vazia) |
| `grep -n 'd+' l2scanner/bosses.py` | 2 ocorrencias, ambas no comentario que PROIBE o uso |
| `grep -rn laranja l2scanner/ tests/ config.toml` | vazio |
| `git diff --stat <base> HEAD` | 3 arquivos: `bosses.py`, `test_bosses.py`, `test_presenca.py` |
| `git diff --stat -- l2scanner/calibrar.py calibrar-tiat.bat tools/ README.md` | vazio — os planos irmaos 01-02 e 01-04 nao foram tocados |
| `git diff --stat -- l2scanner/ponte_*.py l2scanner/mercado_*.py l2scanner/calibrar_mercado.py` | vazio — workstreams paralelos intactos |
| `git diff --stat -- .planning/STATE.md .planning/workstreams/tiat/ROADMAP.md` | vazio — do orquestrador |
| `git diff --stat -- requirements.txt` | vazio — nenhuma dependencia nova |

## Self-Check

Executado antes de escrever esta secao.

**Arquivos afirmados como modificados:**
- `l2scanner/bosses.py` — FOUND
- `tests/test_bosses.py` — FOUND
- `tests/test_presenca.py` — FOUND

**Commits afirmados:** `eec913f`, `b2a4573`, `53f6301`, `acf9cf1` — todos FOUND em `git log`.

## Self-Check: PASSED
