# Roadmap: L2 Party Scanner — Mercado (v1-mercado)

**Workstream:** mercado (`.planning/workstreams/mercado/`)
**Milestone:** v1-mercado — captura e análise de preços do World Exchange
**Created:** 2026-08-27
**Delivery:** console-only (decisão do usuário — comandos WhatsApp de mercado são v2)

## Overview

O milestone transforma cada abertura manual do World Exchange numa coleta de dados passiva. A jornada tem uma porta de entrada inegociável: nada da UI do XM Essence é verificável por pesquisa, então a Fase 1 é um spike de campo — o gravador é consertado primeiro (evidência não-confirmada é o pesadelo documentado do projeto), o USUÁRIO grava sessões reais do mercado, e dessas gravações saem a calibração, os templates e a detecção do painel (o mesmo sinal que protege o detector de morte do incidente 27x). Com fixtures em mãos, a Fase 2 constrói a leitura de página com falha fechada e a Fase 3 constrói a persistência em CSV — em paralelo, porque a Fase 3 só depende do formato da página aceita. A Fase 4 liga tudo: o modo `--mercado` como terceira invocação, o console ao vivo e a análise honesta ("menor pedido visível", nunca "preço de venda").

**Nota de escopo (F0 embutida):** a pesquisa sugeria uma fase 0 de firewall de escopo. Ela foi dobrada na Fase 1: FIRE-01 é um teste de CI + entradas Out of Scope já registradas em REQUIREMENTS.md — minutos de trabalho, sem dependências, e precisa existir ANTES de qualquer código de mercado. Fase própria seria cerimônia.

**Nota de nomenclatura:** os slugs de diretório das fases usam o prefixo `mercado-` (ex.: `phases/01-mercado-fundacao-spike/`) para que escopos de commit nunca colidam com as fases do workstream default.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Fundação — firewall, gravador e spike de campo** - Gravador confiável, gravações reais do World Exchange, calibração/templates e detecção do painel compartilhada com o detector de morte
- [ ] **Phase 2: Leitura de página** - Nome por OCR agrupado por similaridade, dígitos por molde e estabilizador de página contra as fixtures da Fase 1 — falha sempre fechada, preço nunca inventado
- [ ] **Phase 3: Persistência de observações** - Observações dedupadas num CSV legível e importável no Sheets, com firewall de exceção que nunca derruba os alertas
- [ ] **Phase 4: Modo --mercado, análise e console** - Terceira invocação, console ao vivo e estatísticas honestas: mínimo/mediana, destaques, tendência e margem de craft

## Phase Details

### Phase 1: Fundação — firewall, gravador e spike de campo

**Goal**: O usuário consegue produzir evidência de campo confiável do World Exchange, e dessa evidência saem a calibração, os templates e a detecção do painel — o sinal único que também protege o detector de morte.
**Depends on**: Nothing (first phase)
**Requirements**: FIRE-01, FUND-01, FUND-02, FUND-03, DETC-01
**Success Criteria** (what must be TRUE):

  1. O usuário roda uma sessão com `--record` e o contador de frames bate exatamente com os arquivos no disco; um `cv2.imwrite` que falha aparece como erro alto e visível, nunca como frame contado — o usuário pode provar isso enchendo o disco ou apontando para pasta inválida
  2. O usuário gravou sessões reais do World Exchange (fechado, aberto, com scroll, página cheia) e as perguntas de campo estão respondidas por escrito a partir dessas gravações: linhas por página, separador de milhar, moeda, colunas, preço total vs unitário, onde fica o preço médio embutido — incluindo a decisão explícita sobre variantes de encanto (+3 vs +4) na watchlist
  3. O usuário roda a ferramenta de calibração sobre um frame gravado e vê as regiões da janela, a âncora do painel e os templates de dígito persistidos em `calibration.json` — sem editar JSON à mão
  4. No replay da gravação do incidente 27x, o usuário observa o painel de mercado ser reconhecido como "World Exchange aberto" e ZERO alertas de morte disparados — um sinal, dois consumidores, nunca duplicado
  5. Adicionar uma biblioteca de síntese de input (ex.: `pyautogui`) à árvore de dependências faz o teste de firewall falhar — o usuário pode ver o teste vermelho ao tentar

**Plans**: 5 plans (5 waves — a fase é serial por construção: cada wave depende do portão anterior). O 01-05 é fechamento de lacuna, criado após a verificação.

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — (wave 1) Gravador honesto (imwrite checado, resumo com a verdade do disco), modo de gravação da janela completa e o firewall de escopo `tests/test_firewall_escopo.py`

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md — (wave 2) `ROTEIRO-SPIKE.md` + portão executável de conferência, trilho da âncora medido sobre a gravação do incidente 27x, e o **portão externo: o usuário grava as 8 sessões**

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — (wave 3) `SPIKE-RESPOSTAS.md` com evidência resolvida no disco, e o **portão de validação: o usuário valida ou corrige as respostas** (D-04)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-04-PLAN.md — (wave 4) `calibrar-mercado.bat` + `calibrar_mercado.py` (regiões, templates, matriz de confusão), o **portão de calibração: o usuário roda e confere**, e DETC-01 com a regressão do 27x

**Wave 5** *(fechamento de lacuna — blocked on Wave 4 completion)*

- [ ] 01-05-PLAN.md — (wave 5, `gap_closure`) Corte dos **templates de dígito** em `calibrar_mercado.py` (segmentação por projeção de coluna, matriz de confusão dos glifos medida, fusão que nunca apaga) e o **portão humano: a primeira mão a desenhar os retângulos** — fecha a lacuna G-01 da `01-VERIFICATION.md` e desbloqueia FUND-03

**Nota de escopo de DETC-01:** a Fase 1 entrega o SINAL (âncora positiva medida) e sua superfície exibicional em `Observacao`. Os consumidores — o laço `--mercado` e a oclusão conhecida do detector de morte — chegam na Fase 4 junto de DETC-02, por decisão arquitetural registrada em `01-04-PLAN.md` > `<detc01_reconciliation>`. Ligar a oclusão ao rastreador na mesma fase em que a âncora nasce é exatamente a manobra que causou o incidente 27x.

**Bloqueio externo — explícito:** somente o USUÁRIO pode produzir as gravações do World Exchange (conta, cliente e servidor dele). O fix do gravador (FUND-01) vem ANTES de qualquer gravação; depois disso a fase PARA e espera as gravações do usuário. Nenhuma fase seguinte deve ser planejada em detalhe antes das respostas do spike.

### Phase 2: Leitura de página

**Goal**: Contra as fixtures gravadas na Fase 1, o scanner lê por OCR o nome de cada linha visível, agrupa por similaridade e abre série nova para o desconhecido — e lê preços/quantidades por molde de dígito, sem nunca inventar um número.
**Depends on**: Phase 1 (fixtures, calibração, templates e respostas do spike)
**Requirements**: LEIT-01, LEIT-02, LEIT-03, LEIT-05
**Success Criteria** (what must be TRUE):

  1. Rodando o replay contra as fixtures, cada linha visível tem seu nome lido por OCR sobre o recorte da COLUNA DO NOME — nunca a linha inteira — e agrupado por similaridade contra os nomes já vistos; um item que o usuário nunca viu antes aparece como SÉRIE NOVA sem que ele configure nada, e com a tooltip aberta o texto dela não vira nome de item nem cria série fantasma
  2. Os preços e quantidades lidos batem dígito a dígito com o que o usuário vê no frame — separador de milhar tratado como glifo de primeira classe; quando o frame está ilegível, a linha aparece como descartada, nunca como um número plausível. O número NUNCA vem do motor de OCR que lê o nome: medido contra as gravações da Fase 1, ele perde a vírgula decimal e devolve `1650` onde a tela diz `16,50` — erro de 100x com aparência plausível, exatamente o que LEIT-02 existe para impedir
  3. Uma página só é aceita quando dois frames consecutivos concordam nas linhas PARSEADAS; frames bit a bit idênticos são reportados como captura congelada, não aceitos como acordo

**Plans**: 8/8 plans executed (8 waves - a fase e SERIAL por construcao: um portao humano, quatro ondas de medicao que gravam no mesmo arquivo, e so entao o codigo de leitura)

Plans:
**Wave 1**

- [x] 02-01-PLAN.md - (wave 1) As 14 chaves novas de mercado no `calibration.json`, a marcacao propor-e-confirmar das quatro colunas e do molde de cabecalho, e o **portao humano: o usuario recalibra para a GRADE DE NEGOCIACAO**

**Wave 2** *(blocked on Wave 1)*

- [x] 02-02-PLAN.md - (wave 2) Medicao I: `nivel_de_fundo_da_linha` + `tools/medir_oclusao.py` e `tools/medir_leitura_de_glifo.py` - limiar de dispersao, piso do estabilizador, par (piso, margem) de leitura, e o veredito decidivel da guarda de cruzamento

**Wave 3** *(blocked on Wave 2 - as duas ondas gravam no mesmo `calibration.json`, e `os.replace` escreve o arquivo inteiro)*

- [x] 02-03-PLAN.md - (wave 3) Medicao II: os predicados puros do agrupamento em `mercado_catalogo.py`, `tools/medir_agrupamento_de_nome.py`, e o **portao de decisao: de onde vem a assinatura de digitos da chave da serie** (porta de mao unica, tres rotas medidas)

**Wave 4** *(blocked on Wave 3)*

- [x] 02-04-PLAN.md - (wave 4) **TRACER** - uma linha atravessa todas as camadas ate uma pagina aceita; a promocao das primitivas de `calibrar_mercado.py` para `mercado_leitura.py`; a sonda de oclusao ANTES do OCR; e o portao de layout

**Wave 5** *(blocked on Wave 4)*

- [x] 02-06-PLAN.md - (wave 5) A guarda de cruzamento `Total` contra `Unit price x Quantity` - ligada com a tolerancia que o 02-02 mediu, ou desligada com a refutacao escrita no fonte

**Wave 6** *(blocked on Wave 5 - compartilha `mercado_leitura.py` com o 02-06)*

- [x] 02-07-PLAN.md - (wave 6) Medicao III: `tools/medir_brilho_da_quantidade.py` - o piso de brilho PROPRIO da coluna Quantity, medido com rotulo derivado de `Total`/`Unit price`, porque o digito `1` nao se le (tronco a V=177 contra o piso 180) e quantidade `1` e o caso comum do mercado

**Wave 7** *(blocked on Wave 6 - compartilha `mercado_leitura.py`, `calibracao.py` e a calibracao de fixtura com o 02-07)*

- [x] 02-08-PLAN.md - (wave 7) A GUARDA DE LARGURA DE RUN: um run mais largo que o maior molde nao pode ser um glifo so. Hoje ele e casado contra UM molde e vira UM digito — `44` le `4` e `149,44` le `14,44`, as duas com gramatica valida. Medido no censo: **14 quantidades erradas e 55 totais inventados**, a unica falha ABERTA conhecida da fase. A ferramenta mede o vale, o custo da guarda e a folga de cola; a particao entrega o conserto, a guarda e o fallback fechado

**Wave 8** *(blocked on Wave 7 - o replay so mede a fase depois que o piso da Quantity e a guarda de largura existem, senao o rendimento e artefato: as leituras erradas contam como acerto)*

- [x] 02-05-PLAN.md - (wave 8) O catalogo em `.mercado/catalogo-de-nomes.csv` (atomico, defensivo, sem poda), o estabilizador completo (congelamento pela janela inteira + acordo sobre a tupla parseada) e o replay atras do `pytest.skip`

**Bloqueio externo - explicito:** o `calibration.json` da maquina do usuario diz hoje `layout: "adena"`, e a aba Adena **nao tem nome de item** (o OCR da primeira coluna devolve literalmente `'Adena'`). LEIT-01 e LEIT-05 nao tem objeto naquele layout, e o censo das 335 gravacoes da ~25 frames de Adena contra ~283 da grade de negociacao. So o USUARIO pode recalibrar - a fase PARA na Wave 1 e espera.

**Nota sobre as varreduras:** as tasks de medicao (02-02, 02-03, 02-07, 02-08) rodam no checkout PRINCIPAL, nao em worktree. `recordings/` e gitignored e nao se materializa num worktree, e produzir o numero a partir dele e PRODUCAO DE DADO, nao teste. O que roda em qualquer lugar e o teste de regressao, sobre fixture versionada em `tests/fixtures/mercado/`.

### Phase 3: Persistência de observações

**Goal**: Cada página aceita vira linhas num arquivo CSV que o usuário abre e lê — sem duplicar, sem adivinhar, e sem jamais derrubar o núcleo de alertas.
**Depends on**: Phase 1 (respostas do spike informam as colunas). Paraleliza com a Phase 2 — só depende do formato da página aceita, não da leitura pronta.
**Requirements**: PERS-01, PERS-02, PERS-03

> **DECISÃO DO USUÁRIO (2026-08-29): CSV, não SQLite.** O motivo que decidiu não estava na
> mesa quando o roadmap foi escrito: ele quer **ler o dado a olho nu, jogar no Google Sheets,
> e entregar para outra IA analisar**. CSV serve os três nativamente; um `.db` não serve
> nenhum sem ferramenta no meio. As justificativas originais do SQLite (concorrência, dedup
> indexada, consultas por tick) estão analisadas uma a uma em REQUIREMENTS.md — duas já
> tinham caído quando o usuário corrigiu que só o Yazalaque escreve.

**Success Criteria** (what must be TRUE):

  1. Após uma sessão, o usuário abre o CSV num editor de texto e ENTENDE o que está lendo: uma linha por observação, com carimbo do relógio ancorado, preço total e quantidade em colunas separadas (unitário derivado, nunca confundido), preços como inteiros em centésimos
  2. O usuário importa esse mesmo arquivo no Google Sheets e as colunas caem certas — separador `;`, porque a decisão travada da exibição usa vírgula decimal (`62,00`) e um CSV separado por vírgula colapsaria tudo numa coluna. Testado com importação real, não presumido
  3. Reler ou revisitar a mesma página não aumenta a contagem de linhas — o usuário pode contar antes e depois e ver o mesmo número (dedup por chave de conteúdo, conferida em memória antes de escrever)
  4. Com a escrita interrompida no meio de uma linha, a leitura seguinte descarta APENAS a linha truncada, com aviso — nunca trata o arquivo inteiro como corrompido, e nunca aceita o pedaço como observação válida
  5. Com o arquivo propositalmente quebrado (travado, read-only, ou pasta inexistente), o usuário vê o aviso alto de que a feature de mercado desligou — e os alertas de party continuam chegando normalmente

**Plans**: 3/3 plans executed (3 waves — serial por compartilhamento de arquivo: os três tocam `mercado_registro.py` ou dependem do que ele expõe)

**Wave 1**

- [x] 03-01-PLAN.md - (wave 1) `l2scanner/mercado_registro.py` inteiro: a metade pura (chave de dedup e campos do CSV) e a metade de disco (`RegistroDeObservacoes`) — cabeçalho-contrato, as TRÊS redes da leitura de arranque na ordem MEDIDA (o arquivo termina em newline vem ANTES da contagem de campos, que aprova 2 de 5 truncagens), append com `flush` e a escrita que nunca levanta

**Wave 2** *(blocked on Wave 1 — compartilha `mercado_registro.py` e `tests/test_mercado_registro.py` com o 03-01)*

- [x] 03-02-PLAN.md - (wave 2) `montar_registro_de_mercado` no trilho de `montar_gravador` (tenta, degrada com `log.error`, devolve `None`, nunca levanta), o `.mercado/LEIAME.txt` com o roteiro de importação no Sheets, e o comentário do `.gitignore` que passou a falar de dois arquivos

**Wave 3** *(blocked on Wave 2 — usa a montagem do 03-02 para que o aviso alto que o usuário vê seja o MESMO texto da Fase 4)*

- [x] 03-03-PLAN.md - (wave 3) `tools/gerar_observacoes_do_censo.py`: o replay que produz o CSV real para os portões humanos dos critérios 1, 2, 3 e 5 — porque esta fase entrega o registro SEM chamador (DETC-02 é Fase 4), e sem ele o Sheets não teria o que importar

### Phase 4: Modo --mercado, análise e console

**Goal**: O usuário roda a terceira invocação `--mercado` e responde "vale quanto agora?" no console, com estatísticas nomeadas honestamente e evidência sempre visível.
**Depends on**: Phase 2, Phase 3
**Requirements**: DETC-02, LEIT-04, ANAL-01, ANAL-02, ANAL-03, ANAL-04
**Success Criteria** (what must be TRUE):

  1. O usuário inicia `--mercado` como terceira invocação ao lado das duas instâncias de party, e o modo party segue intocado — nenhum comportamento do detector de morte muda, nenhuma competição de recursos perceptível
  2. Com o mercado aberto, o console mostra ao vivo páginas lidas/perdidas e o último item reconhecido; o resumo final conta as duas metades ("li 7, perdi 3")
  3. Para cada item da watchlist, o console responde "vale quanto agora": menor pedido visível e mediana, sempre acompanhados de contagem de evidência e recência ("n=12, visto às 14:32") — a palavra usada é "menor pedido visível", nunca "preço de venda"
  4. Com o mercado aberto, linhas abaixo da mediana histórica aparecem destacadas no console na hora
  5. Tendência por item e margem de craft (receitas do `config.toml`) aparecem com o tamanho da janela de dados explícito, e cada componente da margem mostra sua própria staleness

**Plans**: TBD

## Progress

**Execution Order:**
1 → (2 ∥ 3) → 4 — a Fase 3 pode andar em paralelo com a Fase 2 após a Fase 1.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fundação — firewall, gravador e spike de campo | 5/5 | ✓ Complete | 2026-08-29 |
| 2. Leitura de página | 8/8 | In Progress|  |
| 3. Persistência de observações | 3/3 | In Progress|  |
| 4. Modo --mercado, análise e console | 0/TBD | Not started | - |

## Coverage

Todas as 18 exigências v1 mapeadas (a definição dizia 16; a recontagem na criação do roadmap achou 17; LEIT-05 entrou em 2026-08-29, quando o OCR de nomes voltou ao escopo — FIRE 1, FUND 3, DETC 2, LEIT 5, PERS 3, ANAL 4), cada uma em exatamente uma fase:

| Category | Requirements | Phase |
|----------|--------------|-------|
| Firewall | FIRE-01 | 1 |
| Fundação | FUND-01, FUND-02, FUND-03 | 1 |
| Detecção | DETC-01 | 1 |
| Detecção | DETC-02 | 4 |
| Leitura | LEIT-01, LEIT-02, LEIT-03, LEIT-05 | 2 |
| Leitura | LEIT-04 | 4 |
| Persistência | PERS-01, PERS-02, PERS-03 | 3 |
| Análise | ANAL-01, ANAL-02, ANAL-03, ANAL-04 | 4 |

---
*Roadmap created: 2026-08-27 — awaiting user approval (orchestrator commits)*
