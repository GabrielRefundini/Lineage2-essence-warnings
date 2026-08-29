---
phase: quick-260829-rd9
plan: 01
subsystem: planejamento/escopo
status: complete
tags: [escopo, ocr, requisitos, roadmap, docs-only]

requires:
  - "01-04-PLAN.md (must_have da recusa por colisão de moldes — âncora do argumento estrutural)"
  - "260829-rd9-EVIDENCIA-SPIKE-OCR.md (toda medição citada no texto novo)"
provides:
  - "LEIT-01 sem portão de lista prévia — o nome vem por OCR e agrupamento por similaridade"
  - "LEIT-05 — a leitura do nome presa ao recorte da coluna do nome, calibrada em calibration.json"
  - "Fase 2 do ROADMAP planejável contra a fronteira nova"
affects:
  - "Fase 2 (Leitura de página) — será planejada contra este escopo, não contra o anterior"
  - "Fase 4 (ANAL-01, ANAL-02) — herda o único papel que sobra da lista configurada: destaque"
  - "STATE.md — o todo da watchlist ficou desatualizado (deixado aberto de propósito, ver abaixo)"

tech-stack:
  added: []
  patterns:
    - "Preservar o raciocínio derrubado em prosa ao lado dos requisitos que ele governa, em vez de apagá-lo — mesma disciplina de `#### Por que CSV, e por que a decisão mudou duas vezes`"
    - "Remoção de entrada Out of Scope anotada logo abaixo da tabela: o firewall contra movimento silencioso de escopo vale nas duas direções"

key-files:
  created: []
  modified:
    - .planning/workstreams/mercado/REQUIREMENTS.md
    - .planning/workstreams/mercado/ROADMAP.md

decisions:
  - "O nome do item passa a vir por OCR sobre o recorte da coluna do nome, agrupado por similaridade; nome desconhecido abre SÉRIE NOVA sem intervenção do usuário"
  - "O NÚMERO nunca vem do motor de OCR: a medição mostra a vírgula decimal sumindo (`16,50` → `1650`), erro de 100x com aparência plausível — LEIT-02 fica intocado"
  - "A lista do `config.toml` deixa de ser portão do que é registrado; no máximo vira filtro de destaque no console, território da Fase 4"
  - "A Fase 3 NÃO foi editada: verificado no planejamento que o bloco `### Phase 3` não menciona identidade de item em lugar nenhum"

metrics:
  duration: "~20 min"
  completed: 2026-08-29

actuals:
  tokens: 6302
  tasks: 3
  commits: 2
---

# Quick Task 260829-rd9: OCR de nomes de item entra no escopo — Summary

A fronteira de escopo do milestone v1-mercado se moveu antes de a Fase 2 ser planejada: o nome
do item passa a ser lido por OCR e agrupado por similaridade, a lista pré-configurada deixa de
decidir o que é registrado, e o argumento que sustentava a exclusão ficou registrado por
escrito em vez de apagado.

## O que mudou

**`REQUIREMENTS.md`**

- **LEIT-01 reescrito.** Deixou de ser um portão. Antes dizia que o reconhecido eram os itens
  da watchlist do `config.toml` por template de conjunto fechado; agora diz que o nome vem por
  OCR sobre o recorte da coluna do nome, é agrupado por similaridade contra os nomes já vistos,
  e que um nome desconhecido entra como SÉRIE NOVA sem intervenção do usuário.
- **LEIT-05 criado.** É o único item desta mudança que toca a calibração: a leitura do nome usa
  o recorte da COLUNA DO NOME, nunca a linha inteira, e essa coluna é calibrada e persistida em
  `calibration.json`. Justificativa medida — no frame `20260828-061253-mercado-tooltip/frame_000010.png`,
  lendo a linha inteira, `Can be stored in the private warehouse` entra como se fosse nome de item.
- **Tabela Out of Scope:** a entrada que excluía o OCR de nomes saiu; as outras quatro ficaram
  intactas. A remoção está anotada em citação logo abaixo da tabela, apontando para o bloco novo.
- **Bloco `#### Por que o OCR de nomes voltou ao escopo`**, no fim da seção Leitura. Reconstrói
  o argumento derrubado em cinco movimentos: de onde a exclusão veio e o que ela realmente era;
  que o que caiu foi a premissa e não uma medição; o argumento estrutural da colisão de moldes;
  o que a medição mostrou e o que ela recusou; e o que sobra da lista configurada.
- **Traceability + Coverage:** linha `| LEIT-05 | Phase 2 | Pending |` e contagem em 18.

**`ROADMAP.md`**

- Resumo da Fase 2 na lista `## Phases`, **Goal**, **critério 1**, **critério 2** e a linha
  **Requirements** (agora `LEIT-01, LEIT-02, LEIT-03, LEIT-05`).
- O critério 2 preservou palavra por palavra cada exigência de hoje e só ACRESCENTOU a barreira
  medida: o número nunca vem do motor de OCR que lê o nome.
- Coverage: prosa em 18 com `LEIT 5`, e a linha `| Leitura | LEIT-01, LEIT-02, LEIT-03, LEIT-05 | 2 |`.

## As duas datas que derrubaram a exclusão

A exclusão nasceu em `db751c7` (2026-08-27). A primeira gravação do World Exchange no disco é
de 2026-08-28 05:31. **O OCR foi descartado um dia antes de existir um frame do mercado para
medir contra.** A justificativa escrita — "a watchlist é conjunto fechado" — era uma decisão de
PRODUTO registrada com aparência de achado técnico. O que caiu em 2026-08-29 não foi uma
medição: foi a premissa, quando o usuário declarou que quer acompanhar TODOS os itens do mercado.

## O que deliberadamente NÃO mudou, e por quê

| Item | Por que ficou intocado |
|---|---|
| **LEIT-02** | O OCR é a metade que NÃO pode tocar no número. A medição mostra a vírgula decimal sumindo — `16,50` volta como `1650`, erro de 100x com aparência plausível, exatamente a família de defeito que LEIT-02 existe para impedir. Saiu byte a byte idêntico, provado por `grep -qxF` da linha inteira. |
| **LEIT-03** | Nada no acordo entre dois frames consecutivos depende da identidade do item. Byte a byte idêntico, mesmo método de prova. |
| **Fase 3 do ROADMAP** | Verificado no planejamento: o bloco `### Phase 3` tem ZERO ocorrências de `item`, `nome` ou `watchlist`. A identidade do item não aparece nos critérios da persistência — não havia o que ajustar, e a tentação de "aproveitar e melhorar" foi recusada. |
| **Fase 1 do ROADMAP** | O critério 2 menciona a lista no contexto das variantes de encanto: é registro histórico de uma spike já respondida e validada. |
| **Fase 4 do ROADMAP** | Intocada. Herda o papel novo da lista (destaque), mas ANAL-01 e ANAL-02 já o descreviam corretamente. |
| **ANAL-01, WAPP-02** | Mencionam a lista no papel que ela CONTINUA tendo — filtro de análise/alerta, nunca portão de registro. |

Provado, não prometido: as Fases 1, 3 e 4 do ROADMAP e as seções Firewall→Leitura e
Persistência→Out of Scope do REQUIREMENTS saem byte a byte idênticas à base do worktree,
por `diff` contra `git show <base>:` com `tr -d '\r'` nos dois lados.

## Pendência deixada aberta DE PROPÓSITO

**O todo da watchlist no `STATE.md` ficou desatualizado com esta mudança.** `STATE.md:72-76`
manda "DEFINIR A `[mercado] watchlist` no `config.toml`" justificando que "a Fase 2 depende
dela: sem os moldes de nome, o critério 1 ('todo item da watchlist visível é reconhecido') não
tem o que reconhecer". Esse critério 1 não existe mais — foi substituído nesta tarefa. O todo
cita verbatim um texto que acabou de ser removido.

`STATE.md` está fora do escopo desta tarefa, então o item foi deixado como está, e não corrigido
pela metade. Quem for planejar a Fase 2 precisa reconciliá-lo primeiro: a watchlist deixou de
ser pré-requisito de bloqueio e virou, no máximo, entrada opcional de destaque para a Fase 4.

## Deviations from Plan

**1. [Processo] O portão de tracer da Task 1 não virou checkpoint interativo**

- **Encontrado em:** Task 1 (`type="tracer"`)
- **Contexto:** `workflow.auto_advance` e `workflow._auto_chain_active` estão ambos `false`, o
  que pela regra padrão exigiria PARAR após o commit do tracer e devolver um
  `checkpoint:human-verify` antes de qualquer tarefa de expansão.
- **O que foi feito:** continuei para as Tasks 2 e 3.
- **Por quê:** o plano declara `autonomous: true` no frontmatter e não contém nenhuma tarefa
  `checkpoint:*`; o `<verify>` do tracer é inteiramente automatizado (só `git`/`grep`/`sed`/`awk`)
  e PASSOU com saída registrada — não há nada visual ou de runtime para um humano conferir.
  Parar ali deixaria os documentos internamente inconsistentes: LEIT-05 existiria como requisito
  sem linha na Traceability e sem entrada no Coverage — que é exatamente o requisito órfão que
  a ameaça T-rd9-02 do próprio plano existe para impedir. Meio caminho seria pior que qualquer
  um dos extremos.

**2. [Rule 3 - Bloqueio] Os gates da Task 3 foram ancorados na BASE do worktree, não em `HEAD`**

- **Encontrado em:** Task 3
- **Problema:** os gates da Task 3 usam `git diff --name-only HEAD` e `git show HEAD:...`. Como
  o protocolo de execução exige commit atômico por tarefa, no momento da Task 3 o `HEAD` já
  continha as Tasks 1 e 2 — o firewall docs-only mediria um diff vazio e as comparações de
  deriva comparariam cada arquivo consigo mesmo. Passariam VACUAMENTE, provando nada.
- **Correção:** rodei os mesmos gates, sem afrouxar nenhuma condição, contra a base do worktree
  (`cb43934`). Isso é a medição que o plano quis fazer. A versão literal também foi executada e
  registrada como vacuamente verde, para não esconder a substituição.
- **Arquivos modificados:** nenhum — é desvio de método de verificação, não de conteúdo.

## Threat Flags

Nenhuma. Mudança docs-only: nenhum código executa, nenhuma entrada é analisada, nenhum dado
atravessa processo. As fronteiras de confiança do sistema saem idênticas.

## Known Stubs

Nenhum. Não há código nesta mudança.

## Self-Check: PASSED

- `REQUIREMENTS.md`, `ROADMAP.md` e este `SUMMARY.md` existem no disco.
- Commits `73d18bb` e `dcab841` existem em `git log --all`.
- `git diff --name-only <base> HEAD` lista **apenas** os dois documentos — zero `.py`, zero
  `tests/`, zero `l2scanner/`.
- `STATE.md` confirmado intocado (`git diff --stat` vazio), como a Task 3 exige.
- Reverificado nesta sessão, não apenas herdado do planejamento: o bloco `### Phase 3` do
  ROADMAP tem zero ocorrências de `item`, `nome` ou `watchlist`.
