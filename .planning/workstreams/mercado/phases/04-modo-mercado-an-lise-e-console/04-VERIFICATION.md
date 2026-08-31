---
phase: 04-modo-mercado-an-lise-e-console
workstream: mercado
verified: 2026-08-31T08:30:00Z
status: gaps_found
score: 3/5 must-haves verificados
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "Com o mercado aberto, o console mostra AO VIVO paginas lidas/perdidas e o ultimo item reconhecido"
    status: partial
    reason: "A `linha_ao_vivo` so e emitida quando uma pagina e ACEITA (`if pagina is not None:`), e nao na cadencia de captura. Com o painel aberto e a pagina PERDIDA o console fica mudo — exatamente o momento em que a metade perdida cresce. Medido por execucao: 0 linhas ao vivo num tick de painel aberto com pagina perdida. Alem disso DUAS docstrings de producao afirmam o contrario ('repinta a 1 Hz'), o que viola a doutrina da casa de que o comentario nao pode mentir sobre o codigo."
    artifacts:
      - path: "l2scanner/mercado_modo.py:610"
        issue: "`log.info(linha_ao_vivo(...))` esta DENTRO do bloco `if pagina is not None:`"
      - path: "l2scanner/mercado_console.py:140"
        issue: "docstring de `linha_ao_vivo` diz 'na cadencia da captura - a mesma do resto do scanner'; falso sobre como ela e chamada"
      - path: "l2scanner/mercado_console.py:270"
        issue: "comentario de `SEGUNDOS_ENTRE_SECOES` diz 'a `linha_ao_vivo` ... repinta a 1 Hz'; falso"
    missing:
      - "Emitir a linha ao vivo por TICK (ou ao menos por tick com painel aberto), nao por pagina aceita"
      - "Ou: corrigir as duas docstrings e registrar a mudanca de decisao contra o `04-CONTEXT.md` ('Repinta na cadencia de captura (1 Hz)')"
      - "Teste que afirme a EMISSAO no laco num tick de pagina perdida, e nao so o texto devolvido pela funcao"
  - truth: "Um criterio de aceitacao do 04-01/04-03 afirma que `calibration.json` nunca e escrito"
    status: failed
    reason: "OITAVA INSTANCIA DO PADRAO DE DEFEITO DA FASE. `test -z \"$(git status --porcelain calibration.json)\"` sobre um arquivo GITIGNORED (.gitignore:51) sai vazio SEMPRE — escrito ou nao. O guarda nao consegue detectar a escrita que ele existe para proibir. A VERDADE em si foi confirmada por outro caminho (nenhuma escrita nos modulos de mercado; mtime do arquivo e 30/08 21:37, anterior a rodada de campo de hoje), mas o CRITERIO e vacuo."
    artifacts:
      - path: ".planning/workstreams/mercado/phases/04-modo-mercado-an-lise-e-console/04-01-PLAN.md:533"
        issue: "criterio vacuo sobre arquivo gitignored"
      - path: ".planning/workstreams/mercado/phases/04-modo-mercado-an-lise-e-console/04-03-PLAN.md:441"
        issue: "mesmo criterio vacuo"
    missing:
      - "Afirmar o mtime/hash do `calibration.json` antes e depois do laco, ou varrer o AST dos modulos de mercado por escrita — algo que REPROVE quando a escrita acontecer"
behavior_unverified_items:
  - truth: "O modo `--mercado` roda como TERCEIRA invocacao ao lado das duas de party sem competicao de recursos perceptivel (DETC-02, criterio 1)"
    test: "Abrir as DUAS instancias de party (`vigiar-party.bat`) e o `vigiar-mercado.bat` juntos por 10 minutos com o jogo aberto"
    expected: "Nenhuma borda amarela nas duas de party, log de captura das duas sem erro/atraso novo, CPU dos tres processos estavel no Gerenciador de Tarefas, e nenhum alerta de morte falso"
    why_human: "Contencao entre processos e propriedade do SISTEMA (CPU, GPU, sessoes WGC, agendador do Windows). Nenhum teste automatizado a alcanca — o proprio `tests/test_mercado_firewall_de_fase.py` diz isso por escrito. A rodada de campo de hoje durou ~106 ticks (~1min50) e o usuario nao relatou as duas partys em paralelo."
human_verification:
  - test: "Rodar as tres invocacoes juntas por 10 minutos (portao de campo do DETC-02)"
    expected: "Party intocada; sem borda amarela; sem alerta falso; CPU estavel"
    why_human: "Contencao e propriedade do sistema, nao do programa"
  - test: "Julgar se `REQUIREMENTS.md` pode marcar DETC-02 como Complete com o portao de campo ABERTO"
    expected: "Decisao explicita: reverter para 'codigo pronto, portao aberto', ou manter Complete com override registrado"
    why_human: "E uma decisao de contrato do milestone, nao um fato do codigo"
  - test: "Descomentar o `[[receita]]` do `config.toml` com uma receita REAL sua e rodar o `--mercado`"
    expected: "A secao MARGEM DE CRAFT aparece com a staleness de cada componente e o marcador `<--` no mais velho"
    why_human: "O caminho de producao do ANAL-04 nunca rodou: nao ha `[[receita]]` configurada, entao a margem hoje nao aparece por design. Provado por mim em execucao com receita injetada, nunca pelo arquivo real."
  - test: "Julgar o piso da tendencia (`N_MINIMO_PARA_TENDENCIA = 8`) contra o material real"
    expected: "Decidir se 8 e alto demais"
    why_human: "MEDIDO AGORA sobre o seu `.mercado/observacoes.csv`: das 8 series, 4 alcancam o piso da mediana (5) e apenas 1 alcanca o da tendencia (8). O piso e ESCOLHA declarada; agora existe o primeiro numero para decidir."
  - test: "Julgar a tendencia sobre ofertas de uma MESMA pagina (efeito escada)"
    expected: "Decidir se a frase precisa dizer de quantos INSTANTES distintos as N ofertas vieram"
    why_human: "MEDIDO no seu CSV: `Phantom Mask Sealed` tem n=10 mas apenas 3 carimbos distintos — 7 das 10 vieram da MESMA leitura de pagina, e o grid do World Exchange e ordenado por preco. A regressao sobre o ordinal esta, nessa parte, medindo a escada de precos de uma tela, e sai como `+10.6% ao longo das ultimas 10 ofertas distintas`."
  - test: "Julgar a divergencia declarada do criterio 3 (watchlist como filtro de destaque)"
    expected: "Aceitar (recomendado) e reescrever a letra do criterio 3 no ROADMAP, ou pedir a watchlist de volta como porta"
    why_human: "Decisao tomada por Claude, nao por voce — declarada em voz alta no `04-CONTEXT.md` e no `04-03-SUMMARY.md`"
  - test: "Deixar a tooltip aberta / cobrir a janela durante uma sessao real"
    expected: "Aviso de oclusao e de CAPTURA CONGELADA aparecendo e sumindo; motivos agregados no resumo"
    why_human: "As duas conferencias humanas herdadas da Fase 2 (D14 do 04-01-SUMMARY) continuam abertas"
---

# Fase 4: Modo --mercado, analise e console — Relatorio de Verificacao

**Objetivo da fase:** O usuario roda a terceira invocacao `--mercado` e responde "vale quanto agora?" no console, com estatisticas nomeadas honestamente e evidencia sempre visivel.
**Verificado:** 2026-08-31
**Status:** gaps_found
**Re-verificacao:** Nao — verificacao inicial

## Veredito em uma frase

**A fase entrega o objetivo.** O `--mercado` sobe como terceira invocacao, le,
grava nos dois arquivos e responde "vale quanto agora?" com estatistica honesta
— e eu provei isso RODANDO o console contra o `.mercado/observacoes.csv` real do
usuario, nao lendo SUMMARY. O que fica sao dois defeitos reais (um deles a
oitava instancia do padrao de criterio vacuo), sete itens de conferencia humana,
e uma recomendacao de reverter o `Complete` do DETC-02.

## Verdades Observaveis

| # | Verdade (criterio do ROADMAP) | Status | Evidencia |
|---|---|---|---|
| 1 | `--mercado` como terceira invocacao, modo party intocado (DETC-02) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Flag existe (`__main__.py:2443`) e despacha ANTES do `laco_principal` (`:2539-2542`). `rastreador.py`/`visao.py` sem uma linha de diff — ultimo commit em 2026-08-28 (`f54ba5c`, Fase 1), anterior a esta fase. `JanelaSource(minimum_update_interval=None)` continua o padrao (`captura_janela.py:238`); so o mercado passa 250 ms. Tripwire de import nas duas direcoes. **A metade "sem competicao de recursos" nunca foi observada** — ver item humano. |
| 2 | Console ao vivo com lidas/perdidas + ultimo item; resumo conta as duas metades (LEIT-04) | ✗ PARCIAL | Resumo: PROVADO por execucao — os SETE contadores, as TRES contagens de escrita que nao se somam, os motivos agregados e o p50/p95/maximo. Linha ao vivo: existe e traz `lidas / perdidas / gravadas / ultimo item`, **mas so e emitida quando uma pagina e ACEITA**. Medido: 0 linhas ao vivo num tick com painel aberto e pagina perdida. Ver `gaps`. |
| 3 | "Vale quanto agora": menor pedido visivel e mediana com n e recencia, nomeados honestamente (ANAL-01) | ✓ VERIFICADO | **Provado contra o CSV REAL do usuario** (36 observacoes, 8 series). As 8 series saem com `menor pedido visivel: <total> por <qtd> unidades = <unitario> (derivado) \| n=N \| ha X (dd/mm HH:MM)`. Abaixo do piso o texto diz o que FALTA ("2 de 5 ofertas distintas, faltam 3"). `median_low` sobre `Fraction`. A expressao proibida esta presa por teste COM controle positivo (`test_o_rotulo_do_requisito_ESTA_no_texto`). |
| 4 | Linhas abaixo da mediana historica destacadas no console na hora (ANAL-02) | ✓ VERIFICADO | **Provado por execucao minha** (`destaque_ao_vivo` nunca e citado por nenhum teste): rodei o laco com historico caro semeado e as linhas `Earth Spirit Evolution Stone ABAIXO DA MEDIANA: 3,00 ..., contra mediana de 150,26 ... com n=6` sairam DENTRO do tick. A ordem "julgar antes de gravar" esta presa por um teste que DISCRIMINA (afirma que as duas medianas diferem: 120 antes, 110 depois). |
| 5 | Tendencia com janela explicita e margem de craft com staleness por componente (ANAL-03, ANAL-04) | ✓ VERIFICADO | Tendencia: `tendencia: +10.6% ao longo das ultimas 10 ofertas distintas` sobre o dado real; regressao sobre o ORDINAL, `UNIDADE_DA_JANELA` obrigatoria dentro do proprio resultado. Margem: **provada de ponta a ponta por execucao** — tres linhas de item, cada uma com `n` e idade propria, `<--` no componente velho, e `evidencia mais velha: ha 1 dia (Leonard)` subindo para a linha da margem. Conta exata conferida: `+1.472,64`. |

**Score:** 3/5 verdades verificadas (1 presente mas com comportamento nao exercitado)

## Requisitos

| Requisito | Status | Evidencia |
|---|---|---|
| DETC-02 | ⚠️ PARCIAL | Metade estrutural provada (sem acoplamento, sem import, sem escrita em `calibration.json`, throttle so no mercado, `.bat` proprio). Metade de campo (tres processos por 10 min) ABERTA. **`REQUIREMENTS.md` marca Complete.** |
| LEIT-04 | ⚠️ PARCIAL | Resumo completo e correto; linha ao vivo com cadencia divergente do `04-CONTEXT.md` |
| ANAL-01 | ✓ SATISFEITO | Provado sobre dado de campo real |
| ANAL-02 | ✓ SATISFEITO | Provado por execucao; **zero cobertura de teste do renderizador e da emissao** |
| ANAL-03 | ✓ SATISFEITO | Janela sempre junto; ressalva do efeito escada abaixo |
| ANAL-04 | ✓ SATISFEITO | Codigo provado; caminho de producao nunca exercitado (sem `[[receita]]`), o que e o design declarado |

## Fatos de producao corroborados (leitura, sem escrita)

| Fato relatado | Confirmado |
|---|---|
| 36 observacoes gravadas | ✓ `.mercado/observacoes.csv` tem 37 linhas (36 + cabecalho) |
| 8 series | ✓ `.mercado/catalogo-de-nomes.csv` tem 9 linhas (8 + cabecalho) |
| Os dois arquivos na MESMA sessao | ✓ ambos escritos entre 06:40 e 06:41 — **o terceiro fio esta ligado em producao, nao so em teste** |
| Sessao curta | Observado: ~40 s de painel aberto, ~106 ticks. **Nao alcanca os 10 min do portao do DETC-02.** |

## Verificacao comportamental (executada por mim, somente leitura)

| Comportamento | Resultado | Status |
|---|---|---|
| Suite completa (`pytest tests/ --ignore=tests/test_agenda.py -q`) | 3135 passed, 2 skipped, 130 s | ✓ PASS |
| Seis arquivos de teste da fase | 235 passed | ✓ PASS |
| Console renderizado contra o CSV REAL do usuario | 8 series respondidas com n e recencia | ✓ PASS |
| Margem de craft no laco, com receita real | Bloco completo com staleness por componente e `<--` | ✓ PASS |
| Destaque ANAL-02 dentro do tick | 22 blocos emitidos em 8 ticks | ✓ PASS (com ressalva de ruido) |
| Linha ao vivo com painel ABERTO e pagina PERDIDA | 0 linhas emitidas | ✗ FAIL |
| Exemplo `[[receita]]` comentado do `config.toml`, descomentado e parseado | `Dragon Belt` / rende 1 / Aztac x5 / Leonard x20 | ✓ PASS (sem guarda duravel) |
| `mercado_analise` puro (AST dos imports) | so `difflib`, `statistics`, `dataclasses`, `datetime`, `fractions`, `typing` | ✓ PASS |

## Divergencias declaradas — meu julgamento

### 1. Watchlist como filtro de destaque (criterio 3 "para cada item da watchlist")

**DEFENSAVEL — aceite.** O criterio e anterior a Fase 2, que tirou a watchlist da
porta de entrada. A troca entrega MAIS que a letra: sem configurar nada o usuario
ve as series com mais evidencia (provado: as 8 series reais respondidas), e com
watchlist os itens vem primeiro e marcados sem esconder o resto — o que preserva
a descoberta de item novo que a Fase 2 existe para dar. A divergencia esta escrita
no `04-CONTEXT.md`, repetida como item de julgamento humano no `04-03-SUMMARY.md`
e ancorada no fonte de `ordenar_para_o_console`. **Recomendo reescrever a letra do
criterio 3 no ROADMAP** para o texto parar de contradizer o codigo.

### 2. Pisos de evidencia como ESCOLHA, nunca medicao

**CONFIRMADO no fonte, literalmente.** `N_MINIMO_PARA_MENOR = 1`,
`N_MINIMO_PARA_MEDIANA = 5` e `N_MINIMO_PARA_TENDENCIA = 8` carregam cada um a
frase "ESCOLHA, NAO MEDICAO" com a razao junto. A mesma disciplina aparece em
`HORAS_PARA_MARCAR_COMPONENTE_VELHO = 24`, `SEGUNDOS_ENTRE_SECOES = 60`,
`MS_ENTRE_FRAMES_DO_MERCADO = 250` e `PAGINAS_ENTRE_GRAVACOES_DO_CATALOGO = 20`.

**E agora existe a primeira medicao**, tirada do CSV real: das 8 series,
**4 alcancam o piso da mediana e apenas 1 alcanca o da tendencia**.

### 3. DETC-02 e ANAL-04 marcados Complete com o portao de campo ABERTO

**DETC-02: NAO deveria estar Complete — recomendo reverter.** O texto do requisito
e "vigiar mercado nao degrada nem compete com o modo party". A metade provavel por
codigo esta provada e e excelente; a metade que o requisito literalmente afirma
nunca foi observada, e o proprio `tests/test_mercado_firewall_de_fase.py` diz por
escrito que nenhum teste automatizado a alcanca. Marcar Complete transforma uma
afirmacao nao testada em fato assentado — a classe de erro que este projeto inteiro
combate. Reverter para "codigo pronto, portao de campo aberto", ou manter Complete
com um override que registre o portao como diferido.

**ANAL-04: pode ficar Complete.** O caso e diferente: o codigo esta integralmente
provado (rodei a margem de ponta a ponta) e o silencio em producao e o design
declarado ("sem receita, a margem simplesmente NAO APARECE"). O que falta e um
passo de ACEITACAO do usuario (escrever uma receita real), nao uma lacuna de
verificacao.

### 4. Mensagens de recusa por OCR (commit `21ecdc7`)

**CONFIRMADO e bem escopado.** `mercado_modo.py` agora aponta o
`vigiar-mercado.bat`; `ocr.py`, que e compartilhada, nomeia os DOIS `.bat` em vez
de escolher um. O `vigiar-mercado.bat` inclui o OCR na sonda de dependencias, que
era o buraco medido em campo.

## O padrao de defeito — o que achei

**Achei uma oitava instancia, e ela e do tipo exato descrito.**

`test -z "$(git status --porcelain calibration.json)"` — o guarda de "este modo le,
nunca escreve" — roda sobre um arquivo **gitignored** (`.gitignore:51`). A saida e
vazia sempre, escrito ou nao. O criterio nao consegue detectar a escrita que existe
para proibir. (A verdade em si vale: nenhuma escrita nos modulos de mercado, e o
mtime do arquivo e 30/08 21:37, anterior a rodada de hoje.)

**Um resquicio da forma antiga:** `test -z "$(git diff -- X)"` compara a WORKING
TREE. Os planos aprenderam metade da licao — todos ganharam `|| { echo REPROVADO;
exit 1; }`, que conserta o "diff cru sai 0" — mas nao a outra metade: depois do
commit o comando fica cego. Verifiquei as verdades por outro caminho: `requirements.txt`
intocado desde 28/08 (`0fc57e9`, workstream discord), `rastreador.py`/`visao.py`
desde 28/08.

**Mecanismos instalados e nunca invocados — procurei especificamente:**

| Mecanismo | Chamado em producao? | Coberto por teste? |
|---|---|---|
| `linha_ao_vivo` | Sim, mas so por pagina aceita | Sim (a funcao), nao (a cadencia) |
| `destaque_ao_vivo` | **Sim — provei rodando** | **NAO. Zero referencia em todo `tests/`** |
| `secao_da_margem` / `margem_de_craft` | Sim; devolve vazio hoje (sem receita) | Sim; o teste do laco troca a funcao por espiao que devolve `""` |
| `transicao_do_painel` | Sim, com latch | Sim (conta as linhas) |
| `OrcamentoDoTick` | Sim | Sim |
| `ler_watchlist_do_mercado` / `ler_receitas` | Sim, no arranque | Sim |
| `Catalogo.registrar` + `gravar()` | Sim — **provado em producao pelos 2 arquivos** | Sim |

**Testes fracos, sem consequencia (nao contam como lacuna):**
`test_ela_tem_docstring` (verdadeiro para qualquer funcao documentada) e
`test_a_RAZAO_DA_ORDEM_esta_escrita_no_laco` (`assert "ANTES" in getsource`, que
casa em dezenas de lugares). Nos dois casos a verdade real e sustentada por outro
teste que DISCRIMINA de verdade — em especial
`test_a_referencia_e_a_mediana_de_ANTES_e_nao_a_de_DEPOIS`, que afirma
explicitamente que os dois valores diferem antes de comparar. Isso e o oposto do
par `(6200,48)`/`(4500,100)` que nao discriminava.

## Avisos (nao bloqueiam)

1. **`destaque_ao_vivo` sem um unico teste.** A funcao que desenha a metade
   visivel do ANAL-02 nao e citada por nenhum arquivo de `tests/`. Ela FUNCIONA
   (provei), mas nada a protege de uma regressao.
2. **O destaque nao tem latch e repete para oferta duplicada.** Medi 22 blocos
   emitidos em 8 ticks para uma serie. Na rodada real houve 274 duplicadas contra
   36 observacoes: com o painel aberto sobre um item barato, o mesmo bloco
   emoldurado sai a cada tick e afoga a linha ao vivo. A fase colocou latch em
   toda outra mensagem repetitiva (`transicao_do_painel`, `_layout_ja_recusado`,
   `_congelamento_ja_avisado`) e nao aqui.
3. **Efeito escada na tendencia.** No CSV real, `Phantom Mask Sealed` tem n=10 mas
   apenas **3 carimbos distintos** — 7 das 10 ofertas vieram da MESMA leitura de
   pagina. Como o grid do World Exchange e ordenado por preco, o ordinal dentro de
   uma pagina E o ranking de preco, e a regressao mede a escada de uma tela em vez
   de movimento no tempo. Sai como `+10.6%`. O rotulo "ofertas distintas" (nunca
   "ao longo do tempo") ja e a mitigacao escolhida e esta correto; a ressalva e que
   o raciocinio da docstring previu o problema do carimbo quase-constante e nao
   previu este.
4. **`ler_watchlist_do_mercado` e `ler_receitas` ignoram o `config.local.toml`.**
   Leem so `ARQUIVO_CONFIG`, enquanto `ler_membros` e `ler_personagem_do_jogo`
   implementam precedencia com o local vencendo. O usuario **tem** um
   `config.local.toml` (hoje so com `[[membro]]`, entao nao ha bug vivo). Um
   `[[receita]]` escrito la seria silenciosamente ignorado — exatamente o desfecho
   mudo que o comentario do proprio codigo declara inaceitavel.
5. **O `[[receita]]` comentado nao tem guarda duravel.** Ja declarado em
   `deferred-items.md`. Conferi que ele parseia hoje; nada garante amanha.
6. **Uma serie do dado real e um homonimo de encanto separado corretamente**
   (`Phantom Mask Sealed`, `+1`, `+2`, `+3` como quatro series) — o casamento exato
   do ANAL-04 esta certo, e o teste `test_prefixo_de_encanto_NAO_CASA_com_o_item_base`
   prende isso.

## Anti-padroes

Nenhum marcador de divida (`TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER`) nos arquivos
da fase. As ocorrencias de `TODO` sao a palavra portuguesa "todo/todos" em prosa.

## Escopo de outro workstream

Nada em `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `tests/test_bosses.py`
ou nos commits `01-01`/`discord-01` foi contado contra esta fase. O commit
`21ecdc7` toca `ocr.py`, que e compartilhada — a mudanca la nomeia os dois modos e
nao degrada o caminho da party.

## Diferimento

Fase 4 e a ULTIMA do milestone `v1-mercado`. Nao ha fase posterior para absorver
nenhuma lacuna: as duas do bloco `gaps` sao acionaveis agora ou viram divida
declarada do milestone.

---

*Verificado: 2026-08-31 — verificacao goal-backward, somente leitura, sem escrita em `.mercado/` e sem rodar o modo contra o jogo*
