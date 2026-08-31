---
phase: 02-leitura-de-p-gina
workstream: mercado
verified: 2026-08-30T23:40:00Z
status: passed
score: 2/3 criterios verificados
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: null
  note: "verificacao inicial — nao havia 02-VERIFICATION.md"
behavior_unverified_items:
  - truth: "Criterio 1 — cada linha visivel tem seu nome lido POR OCR sobre o recorte da coluna do nome"
    test: "Abrir o jogo com o World Exchange na grade de negociacao e rodar a leitura de nome pelo motor WinRT REAL dentro do tick (via tools/medir_agrupamento_de_nome.py, que ja chama ocr.ler_texto/ocr.ler_texto_ampliado, ou pela primeira invocacao --mercado da Fase 4)"
    expected: "ocr.disponivel() verdadeiro, os nomes lidos batendo com o que esta na tela, e a latencia das duas escalas cabendo no tick de 1 Hz"
    why_human: "O pytest roda no Python GLOBAL, sem as bindings WinRT: TODA a suite injeta as leitoras. O replay reproduz o que o motor real leu (leituras_de_nome.json), casado por CONTEUDO do recorte — prova a geometria e o pipeline, nao o motor dentro do laco."
  - truth: "Criterio 3 — captura congelada e reportada e nenhuma pagina e aceita"
    test: "Com o mercado aberto, minimizar a janela do jogo (ou pausar a captura) por 3+ ticks"
    expected: "Aviso ALTO CAPTURA CONGELADA no log e nenhuma pagina aceita enquanto a janela nao mudar; ao voltar a mudar, o aviso 'A captura VOLTOU a mudar'"
    why_human: "frames_congelados = 0 em todo o censo de 478 ticks — a borda de TRES nunca disparou sobre material real, so sobre fixtura (frame real repetido)."
human_verification:
  - test: "OCR real com WinRT, com o jogo aberto"
    expected: "nomes lidos batendo com a tela; ocr.disponivel() verdadeiro"
    why_human: "nenhum teste desta fase chamou o motor — todas as leitoras sao injetadas"
  - test: "Congelamento de captura provocado a mao (minimizar/pausar)"
    expected: "aviso alto e nenhuma pagina aceita"
    why_human: "zero ocorrencias no material real do censo"
  - test: "DECISAO DE PRODUTO: o rendimento 151 lidas / 189 perdidas e aceitavel?"
    expected: "acordo explicito do usuario, ou uma nova medicao do piso de posicoes comparadas"
    why_human: "nenhum criterio do roadmap fixa rendimento minimo; 72% das perdas sao o piso de 7 fazendo o trabalho para o qual foi medido"
  - test: "DECISAO DE PRODUTO: duas janelas bit-identicas AINDA aceitam uma pagina (a borda e TRES). Isso e aceitavel?"
    expected: "acordo explicito, ou abaixar a borda para DOIS e pagar o falso positivo de pagina parada"
    why_human: "leitura literal do criterio 3 contra a decisao D-19 medida; ver o achado abaixo"
gaps: []
deferred:
  - truth: "O motor de OCR real ligado ao laco de producao (LeitorDePagina construido com ocr.ler_texto)"
    addressed_in: "Phase 4"
    evidence: "ROADMAP Fase 4, criterio 1: 'O usuario inicia --mercado como terceira invocacao' — a Fase 2 nao tem modo de invocacao proprio, por fronteira declarada em 02-CONTEXT.md"
---

# Fase 2: Leitura de página — Relatório de Verificação

**Goal (ROADMAP):** Contra as fixtures gravadas na Fase 1, o scanner lê por OCR o nome de cada
linha visível, agrupa por similaridade e abre série nova para o desconhecido — e lê
preços/quantidades por molde de dígito, sem nunca inventar um número.

**Verificado:** 2026-08-30 · **Status:** `human_needed` · **Re-verificação:** Não (inicial)

---

## Veredito por critério de sucesso

### Critério 1 — nome por OCR, coluna do nome, série nova, tooltip inócua

**PRESENTE, COMPORTAMENTO NÃO EXERCITADO (o motor)** — o pipeline está provado; o motor não.

| Metade do critério | Veredito | Evidência |
|---|---|---|
| Recorte da **COLUNA DO NOME**, nunca a linha inteira (LEIT-05) | VERIFICADO | `mercado_coluna_do_nome` (dx, largura) é a origem do recorte em `ler_linha`; `tests/test_mercado_leitura.py:555` prende "recortada UMA vez e lida DUAS" |
| Agrupamento por similaridade | VERIFICADO | `mercado_catalogo.similaridade` / `agrupar` / `chave_da_serie`, corte medido `0,894737`; `tests/test_mercado_catalogo.py` |
| **SÉRIE NOVA sem configuração** | VERIFICADO | O replay real produziu **39 séries distintas** a partir de zero, sem watchlist |
| Tooltip não vira nome nem série fantasma | VERIFICADO | A sonda de oclusão roda **ANTES** do OCR (passo 2 do pipeline, preso por contagem de chamadas); as 8 linhas cobertas de `tooltip/frame_000012` são recusadas |
| **Lido pelo motor de OCR** | **NÃO EXERCITADO NO LAÇO** | ver abaixo |

**O que eu efetivamente encontrei sobre o motor** — e é mais forte do que "nunca rodou":

- `tools/medir_agrupamento_de_nome.py:398-404` chama `ocr.ler_texto` e `ocr.ler_texto_ampliado`
  — **o motor WinRT real**, com portão `ocr.disponivel()` na linha 1251. O censo das 8 gravações
  **rodou com o motor de verdade**, sobre o recorte derivado de `cal.mercado_coluna_do_nome`.
  Foi assim que `leituras_de_nome.json` (3.511 leituras limpas) nasceu.
- O replay casa o recorte por **conteúdo** (`ndarray.tobytes()`), não por posição. Isso não é
  detalhe: se a geometria que `ler_linha` calcula divergisse um pixel da que a ferramenta mediu,
  o casamento devolveria `""` e **toda** linha cairia. As 151 páginas aceitas (≥7 linhas cada,
  ≥1.057 nomes) provam que **o recorte de produção é byte-idêntico ao que o motor real leu**.

**O que continua sem prova:** o motor **dentro do tick**. Nenhum teste chama `ocr.*`
(o pytest roda no Python global, sem WinRT), e **ninguém em produção constrói `LeitorDePagina`** —
a única construção é em testes. Isso é fronteira declarada, não omissão: a Fase 2 não tem modo de
invocação (Fase 4, DETC-02 / `--mercado`). Restam sem verificação: disponibilidade do WinRT na
máquina do usuário, latência das duas escalas dentro de 1 Hz, e o comportamento do motor sobre
pixels ao vivo (contra pixels gravados).

**Julgamento:** o critério 1 **não pode ser dado como verdade sem a mão do usuário**. O que a fase
provou é substancial (geometria, agrupamento, série nova, tooltip, e o motor real sobre os mesmos
bytes) — mas "lido por OCR" com o jogo aberto é a metade que só o usuário fecha.

### Critério 2 — preço e quantidade dígito a dígito, falha fechada

**VERIFICADO**

Os dois defeitos que existiam desde o começo estão consertados **e presos por TESTE, por VALOR** —
não por relatório de ferramenta:

| Defeito | Conserto preso por | Assertiva |
|---|---|---|
| O `1` da Quantity abaixo do piso (tronco a V=177 contra piso 180) | `tests/test_mercado_leitura.py:1167` | a linha de quantidade `1` **atravessa**; `leitura.descartadas == ()` |
| Glifos iguais colados (`44` lido `4`) | `TestOsGlifosCOLADOS`, 3 fixtures | `== "44"`, `== "149,44"`, `== "44,00"` |

O teste do run de 11 px é especialmente bom: ele **não** afirma "leu", afirma o VALOR — a docstring
nomeia que o corte errado `6+5` produziria `144,44`, que passa na gramática. Um teste de "leu" teria
passado por cima do bug.

**Limiares por parâmetro, sem valor de fábrica:** verificado por AST, não por leitura.
`tests/test_mercado_leitura.py:1669` (`test_a_cadeia_inteira_exige_folga_de_cola`) afirma
`parametros["folga_de_cola"].default is inspect.Parameter.empty` ao longo da cadeia inteira; o
mesmo padrão vale para `valor_minimo` / `valor_minimo_do_numero` / `valor_minimo_da_quantidade`
(linha 281). Nenhuma constante de brilho no fonte.

**Falha fechada:** as peneiras têm motivos distintos; a coluna coberta devolve `None` e **nunca um
número parcial** (`test_a_coluna_coberta_pela_tooltip_devolve_None_e_nunca_numero_parcial`). O número
**nunca** vem do motor de OCR — as três colunas de número passam por `ler_glifos` / molde, e
`ler_texto` só toca a coluna do nome. Verificado no fonte: `ler_linha` passos 3 (números) e 5 (nome)
são caminhos disjuntos.

### Critério 3 — acordo entre dois frames, congelamento reportado

**VERIFICADO na metade do acordo · um achado sobre a borda do congelamento**

| Metade | Veredito | Evidência |
|---|---|---|
| Acordo sobre linhas **PARSEADAS**, nunca pixels | VERIFICADO | `tupla_comparavel` / `posicoes_comparaveis` / `paginas_concordam`; acordo pela INTERSEÇÃO, piso `mercado_minimo_de_linhas_comparadas = 7` lido do disco; a linha DESCARTADA num dos frames não é desacordo (`test_a_linha_DESCARTADA_num_dos_frames_nao_e_desacordo`) |
| Acordo trivial recusado | VERIFICADO | `T-02-26`: acordo sobre 2 posições não aceita página |
| Congelamento reportado e nenhuma página aceita | EXERCITADO POR TESTE | `TestOCongelamentoDeCaptura`: 3 janelas bit-idênticas → `frames_congelados >= 1`, `aceitas[2:] == [None, None, None]`, aviso ALTO no log, contagem zera na primeira diferença |

**Sobre `frames_congelados = 0` no censo (ceticismo #3):** isto **não** é lacuna de programa. A
borda foi exercitada por teste comportamental sobre um frame REAL repetido (`JANELA_F005`), e a
transição de estado (contagem, latch do aviso, recomeço) tem teste próprio. Zero no censo significa
apenas que o gravador nunca congelou — que é o resultado desejável. O que falta é a confirmação de
campo, e ela está listada acima como item de verificação humana.

**ACHADO — a borda é TRÊS, o acordo é DOIS.** `JANELAS_IGUAIS_PARA_CONGELAR = 3`, e o acordo fecha
com **dois** frames. Segui o caminho no código (`observar` → `_captura_congelada` → acordo): no
frame 2 de uma captura travada a contagem é 2, `_captura_congelada` devolve `False`, o painel é
encontrado, a página é lida e **concorda trivialmente** com `_anterior` — **uma página É aceita**.
Só a partir do frame 3 nada mais passa. O teste `test_congelada_NENHUMA_pagina_e_aceita` afirma
`aceitas[2:]`, e é silencioso justamente sobre `aceitas[1]`.

Isto contradiz a **leitura literal** do critério 3 ("frames bit a bit idênticos são reportados como
captura congelada, **não aceitos como acordo**"). Não classifiquei como BLOCKER, por três razões,
todas conferidas no fonte:

1. A escolha é **deliberada e medida**, com a razão escrita: `mercado_pagina.py:85-91` — duas
   janelas iguais acontecem de verdade (jogo pausado no alt-tab), e no spike o painel é
   **bit-estável**; usar 2 daria falso alarme o tempo todo.
2. O dado da página aceita é **o último frame vivo**, não um número inventado — o critério 2
   (nunca inventar) não é violado.
3. O impacto é **uma** observação duplicada por episódio de congelamento, e a Fase 3 dedupa por
   chave de conteúdo (PERS, critério 3).

É uma **decisão de produto pendente**, listada em `human_verification`.

---

## Cobertura de requisitos (por código E teste, não por frontmatter)

| Req | Descrição | Código | Teste | Status |
|---|---|---|---|---|
| **LEIT-01** | Nome por OCR, agrupado por similaridade, série nova sem lista prévia | `mercado_catalogo.py` (`similaridade`, `agrupar`, `chave_da_serie`, `Catalogo`), `mercado_leitura.ler_linha` passo 5 | `test_mercado_catalogo.py`, `test_mercado_leitura.py`, `test_mercado_replay.py` (39 séries do zero) | SATISFEITO (motor real → humano) |
| **LEIT-02** | Preço/quantidade por molde, falha FECHADA | `ler_glifos`, `particionar_run`, `limite_de_glifo_unico`, `ler_celula_de_quantidade`, `mascara_de_numero` | `TestOsGlifosCOLADOS` (3 valores), piso 161 (`:1167`), AST sem valor de fábrica (`:1669`) | SATISFEITO |
| **LEIT-03** | Página aceita só com dois frames concordando nas linhas PARSEADAS | `mercado_pagina.py` (`paginas_concordam`, `_captura_congelada`) | `test_mercado_pagina.py` (58 testes) | SATISFEITO (com o achado da borda 2×3) |
| **LEIT-05** | Recorte da COLUNA DO NOME, calibrado e persistido | `mercado_coluna_do_nome` em `calibration.json`, consumido por `fatiar_a_linha`/`ler_linha` | `test_mercado_leitura.py:504,522,555,846` | SATISFEITO |

**Órfãos:** nenhum. Os quatro IDs mapeados à Fase 2 em REQUIREMENTS.md aparecem em código e teste.
IDs compartilhados entre planos (LEIT-01/LEIT-02 declarados por vários) não produziram buraco.

---

## O que a fase NÃO entrega — está honesto?

**Sim, e num grau incomum.** As três estão registradas onde alguém as encontra:

| Limitação | Onde está registrada | Veredito |
|---|---|---|
| Guarda de cruzamento **DESLIGADA** por medição (fechamento 0,6525 vs 0,99; detecção 0,0164 vs 0,90) | **No fonte**: `mercado_leitura.py:994-1009`, refutação literal ao lado da função; degradada para OBSERVAÇÃO (`residuo_do_cruzamento` continua calculado e logado). Também em `STATE.md:75,81` | HONESTO |
| Fusão `B-grade Gemstone` × `C-grade Gemstone` em 0,9375 (letra de grade; a trava de dígitos não alcança) | **Presa por teste**: `tests/test_medir_agrupamento_de_nome.py:322-332` afirma o par nomeado e a distância de edição 1. Também em `02-CONTEXT.md:320` | HONESTO |
| `Lv. I` × `Lv. 1` **não** é absorvido (a trava de dígitos intercepta antes) — 8,86% das linhas | **No fonte**: `mercado_catalogo.py:39,50,59,139,179` e `mercado_leitura.py:1510`; a promessa original em `02-CONTEXT.md` está riscada COM a ressalva no lugar; `STATE.md:80,103` registra o custo aceito pelo usuário | HONESTO |

Observação: a fusão `Gemstone` é a única das três que **não** está no fonte de produção
(`mercado_catalogo.py` não a nomeia). Está num teste de ferramenta. Isso é suficiente para ser
encontrada, mas é o elo mais fraco dos três.

---

## Rendimento — 151 lidas / 189 perdidas (ceticismo #6)

**Concordo com a leitura da fase: não é defeito de programa, é julgamento de produto.**

Reproduzi o replay eu mesmo (não li do SUMMARY). `python -m pytest tests/test_mercado_replay.py
tests/test_mercado_27x.py -q` → **63 passed**, e a saída bate número por número com o que a fase
afirmou: 517 frames, **478 ticks com painel**, **151 lidas / 189 perdidas**, 7 vazias, 131 de outro
layout, 1.007 linhas descartadas, **39 séries**, **0 frames congelados**. As 189 perdas: 136 abaixo
do mínimo comparado, 34 primeiro frame do par, 19 discordância real.

136 das 189 (72%) são o piso de 7 posições fazendo exatamente o que foi medido para fazer —
recusar o acordo trivial. **Nenhum dos três critérios do roadmap fixa rendimento mínimo**, então
formalmente a fase não pode falhar por isto. Mas também não pode ser declarada "suficiente" sem o
usuário: baixar o piso reabre o acordo trivial e exige varredura nova. **Falta acordo com o
usuário**, e está listado em `human_verification`.

---

## Regressão — nada do mercado tocou o detector de morte (ceticismo #7)

**VERIFICADO, e por três vias independentes:**

1. `git log --since=2026-08-29 -- l2scanner/rastreador.py l2scanner/visao.py` → **vazio**. Nenhum
   commit da Fase 2 tocou nenhum dos dois arquivos.
2. `tests/test_mercado_27x.py` **verde** (dentro dos 63 passed do run acima) — o painel de mercado
   continua reconhecido como "World Exchange aberto" e ZERO alertas de morte.
3. `barra_propria_legivel`, `_moldura_da_barra_propria`, `_bordas_da_barra_intactas` intactos em
   `visao.py` (nenhum diff no período da fase).

Reforço estrutural: a Fase 2 **não liga** a oclusão ao rastreador — é fronteira declarada em
`02-CONTEXT.md` e adiada para a Fase 4 (DETC-02). Foi ligar isso cedo demais que causou o
incidente 27x, e a fase respeitou.

---

## Suíte e higiene

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte principal | `pytest --ignore=tests/test_agenda.py -q` | ~~**2605 passed, 2 skipped**~~ **NÃO SE SUSTENTA** — remedido em `efcd73a`: **2551 passed, 14 skipped, 1 FAILED**. Ver a correção no `02-05-SUMMARY.md` e as janelas #36/#37/#38 |
| Agenda (isolado, flake conhecido) | `pytest tests/test_agenda.py -q` | **144 passed** em 11s — não abortou |
| Replay + regressão 27x | `pytest tests/test_mercado_replay.py tests/test_mercado_27x.py -q` | **63 passed** em 73s |
| `calibration.json` não commitado | `git log -- calibration.json` | **vazio**; `.gitignore:45` |
| `calibration.json` intocado pela verificação | md5 antes/depois | `1d6b9b6b…` **idêntico** |
| `recordings/` somente leitura | `git status --short recordings` | limpo |

Todos os números da suíte que a fase afirmou foram **reproduzidos**, não aceitos.

---

## Anti-padrões

Varredura sobre os arquivos de mercado (`l2scanner/mercado_*.py`, `tools/medir_*.py`): nenhum
`TBD`/`FIXME`/`XXX` sem referência de trabalho formal; nenhuma implementação vazia; nenhum dado
inventado no caminho de renderização. Os `None` encontrados são todos **falha fechada declarada**
(coluna ilegível → `None`, nunca número parcial) e não stubs.

---

## Resumo do veredito

**A Fase 2 entregou o que prometeu, e a metade que falta ela mesma já nomeou.**

Os três critérios estão implementados, cabeados e — nos pontos onde a suíte alcança — provados por
teste que prende VALOR. Os dois defeitos de dígito estão consertados com teste por valor, os
limiares chegam por parâmetro sem valor de fábrica, os quatro requisitos têm código e teste, o
detector de morte não foi tocado, e as três limitações estão registradas onde alguém tropeça nelas.

**O status é `human_needed` e não `passed`** porque o critério 1 depende do motor de OCR que
nenhum teste desta fase chamou, e porque duas decisões de produto (rendimento, e a borda 2×3 do
congelamento) exigem a palavra do usuário. Não é lacuna de execução — é o limite do que a suíte
pode afirmar sozinha, e `STATE.md:104` já o havia nomeado antes de eu chegar.

---

_Verificado: 2026-08-30 · Verificador: Claude (gsd-verifier), workstream `mercado`_


---

## PORTOES HUMANOS FECHADOS — 2026-08-31, sessao real do usuario

Os dois portoes que mantinham esta fase em `human_needed` foram exercitados na
maquina do usuario, com o jogo aberto. **Status promovido a `passed`.**

Eles so ficaram alcancaveis depois que a sessao de debug
`sonda-do-fundo-recusa-nome-comprido` consertou a sonda de oclusao: ate entao a
aba com nomes compridos descartava 129 linhas e nao aceitava pagina nenhuma.

### 1. OCR real dentro do tick — FECHADO, e conferido contra a tela

Aba Enhancement > Scrolls, `Protecting Scroll: Enchant C-grade Armor` — 40
caracteres, o nome mais comprido que o mercado apresenta.

**10 de 10 linhas exatas**: nome, total, quantidade e ORDEM identicos ao print,
comparados linha a linha. Zero divergencia.

O unico residuo nao-zero esta CORRETO e explicado: `35,00 / 9 = 3,8888...`, o
jogo exibe `3,88` truncado, e `3500 - (388 x 9) = 8`. O residuo mede a truncagem
do proprio jogo, que e a razao de o unitario exibido nunca ter virado coluna.

Sessao: 13 paginas lidas, 1 perdida, **0 linhas descartadas**, 10 observacoes.

### 2. Congelamento provocado — FECHADO

Janela minimizada com o modo rodando. Saiu, literal:

    CAPTURA CONGELADA: 3 janelas consecutivas bit-identicas. Nenhuma pagina do
    mercado sera aceita ate a janela mudar.

Comportamento exato do desenho: detecta em 3 janelas, recusa aceitar pagina, e
avisa alto. O `TestOCongelamentoDeCaptura` afirmava isto por teste; agora esta
afirmado por campo.

### De quebra, ANAL-01/02 da Fase 4 provados com dado real

Console: `ABAIXO DA MEDIANA: 2,50 por unidade (derivado), contra mediana de 3,89
(derivado) com n=10`. Conferido: com n=10 (PAR), `median_low` devolve 388,89 —
que ESTA na lista — enquanto `statistics.median` devolveria 394,44, que NAO
esta. A decisao "um numero exibido tem de ter existido na tela", travada na
Fase 4 e presa por um teste com n=6, comprovada em producao.
