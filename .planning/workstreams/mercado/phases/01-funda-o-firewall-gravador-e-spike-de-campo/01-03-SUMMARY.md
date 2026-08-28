---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 03
subsystem: testing
tags: [spike, analise-de-campo, evidencia, matchTemplate, ancora, mercado, portao]

requires:
  - phase: 01-01
    provides: "--record-janela e o gravador que so conta escrita confirmada"
  - phase: 01-02
    provides: "ROTEIRO-SPIKE.md, molde_da_ancora.png, mercado_visao.casamento_da_ancora, limiar 0.73"
provides:
  - "SPIKE-RESPOSTAS.md: as 9 perguntas de campo respondidas e seladas sobre os 335 frames, 41 caminhos resolvidos no disco"
  - "tools/conferir_spike_respostas.py: portao que resolve cada frame citado com Path.exists() e recusa selo positivo sem evidencia"
  - "MEDICAO QUE MUDA DESENHO: a margem de campo da ancora e NEGATIVA (-0,0643) -- as classes aberto/fechado se sobrepoem"
  - "MEDICAO: o painel percorre 827 x 831 px em 34 posicoes distintas -- busca em faixa descartada"
  - "MEDICAO: tres layouts de coluna distintos, nao um; e a virgula e milhar E decimal na mesma linha"
  - "D-05 validada em frame real, com o custo de errar medido (7,02 a 100,00 para o mesmo nome)"
affects: [01-04 calibracao e deteccao do painel, fase 2 leitura da grade e estabilizador de pagina, fase 3 banco de precos, fase 4 consumidor de oclusao]

actuals:
  tokens: 9473
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Portao de evidencia: RESOLVER o caminho no disco, nunca so casar o formato"
    - "Selo por resposta (VERIFICADO / PARCIAL / NAO RESPONDIDO) contado so dentro das secoes numeradas, para a legenda nao satisfazer o portao"
    - "Juiz INDEPENDENTE: quando a medicao julga a si mesma, trocar de regiao -- manchas de arte opaca julgam a faixa de titulo"
    - "Tomar o MAXIMO sobre manchas espalhadas quando o ruido esperado e LOCAL (tooltip perto do cursor)"
    - "--raiz / --pasta-base em toda ferramenta que le recordings/, porque worktree nao materializa arquivo gitignored"

key-files:
  created:
    - .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/SPIKE-RESPOSTAS.md
    - tools/conferir_spike_respostas.py
  modified: []

key-decisions:
  - "A ancora do 01-04 nao pode ser so a faixa de titulo: a margem de campo e negativa, entao precisa de um segundo sinal (manchas de arte opaca, aceitando a melhor)"
  - "A busca do painel e na janela inteira com cadencia limitada e memoria da ultima posicao, nao em faixa"
  - "mercado_grade precisa gravar QUAL layout esta lendo: sao tres conjuntos de coluna diferentes"
  - "O banco da Fase 3 guarda Total e Quantity e DERIVA o unitario -- o unitario exibido e arredondado a 2 casas e nao reconstroi o total"
  - "A desambiguacao da virgula vem do sufixo (XM Coin / Adena), nao do numero"
  - "status: halted -- a Task 2 e o portao humano de D-04 e nada do 01-04 roda antes dele"

patterns-established:
  - "Prova de vermelho por mutacao antes de confiar no verde: 3 mutacoes, e uma delas encontrou um bug REAL no proprio portao"
  - "Quando a medicao automatica contradiz o olho, olhar primeiro: a primeira medicao de truncamento deu 262/263 px e o vencedor era uma tooltip"

requirements-completed: []

coverage:
  - id: D1
    description: "SPIKE-RESPOSTAS.md com as 9 perguntas de campo respondidas, cada uma com um selo e frames que existem no disco"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "python tools/conferir_spike_respostas.py --raiz <checkout> -> exit 0, 41 caminhos resolvidos, tabela de 9 secoes"
        status: pass
    human_judgment: true
    rationale: "O portao prova que os frames citados EXISTEM; ele nao prova que a resposta descreve corretamente o que o frame mostra. So quem conhece o jogo compara a resposta com a realidade -- e e exatamente isso que a Task 2 (D-04, gate blocking-human) existe para colher. Ate o 'validado' do usuario, todo selo positivo deste documento e uma PROPOSTA."
  - id: D2
    description: "Portao executavel que recusa evidencia nao confirmada: caminho inventado, selo positivo sem frame, e legenda contando como resposta"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "mut_a_caminho_inventado.md (caminho de formato perfeito, pasta inexistente) -> exit 1 nomeando `secao 8` e o caminho"
        status: pass
      - kind: other
        ref: "mut_b_selo_sem_frame.md (secao 4 selada VERIFICADO, zero citacoes) -> exit 1 nomeando a secao e a linha"
        status: pass
      - kind: other
        ref: "mut_c_oito_secoes.md (secao 3 des-numerada) -> exit 1 com [1,2,4,5,6,7,8,9]; a legenda NAO repos a nona"
        status: pass
      - kind: other
        ref: "documento real -> exit 0 com 6 VERIFICADO, 2 PARCIAL, 1 NAO RESPONDIDO"
        status: pass
      - kind: other
        ref: "Secao.selos aceita `NAO RESPONDIDO` com e sem til (o usuario vai editar no portao da Task 2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Resposta da pergunta A1 (posicao do painel), que decide a forma da ancora do 01-04"
    requirement: "DETC-01"
    verification:
      - kind: other
        ref: "censo da ancora nos 335 frames: 34 posicoes distintas, x 412..1239, y 79..910, com frame citado em cada extremo"
        status: pass
    human_judgment: false
  - id: D4
    description: "A margem de campo da ancora do painel, medida com juiz independente da propria ancora"
    requirement: "DETC-01"
    verification:
      - kind: other
        ref: "classificacao dos 45 frames sub-limiar por manchas de arte opaca: 19 falsos negativos, pior positivo 0.4110 < melhor negativo 0.4753"
        status: pass
    human_judgment: true
    rationale: "O numero e reprodutivel, mas a conclusao ('o limiar sozinho nao serve') redesenha a deteccao do 01-04. Merece a leitura de quem vai construi-la, e os dois piores frames foram conferidos a olho justamente para que a conclusao nao dependa so do juiz automatico."
  - id: D5
    description: "Validacao da D-05: o encanto renderiza como prefixo `+N ` no nome"
    requirement: "FUND-02"
    verification:
      - kind: other
        ref: "recordings/20260828-063752-mercado-aberto/frame_000000.png -- 10 linhas do mesmo item base em +0/+2/+4/+5/+6/+7"
        status: pass
    human_judgment: true
    rationale: "A renderizacao esta num frame e e inequivoca. O que precisa do usuario e a parte que o frame NAO mostra: se um nome mais longo que 263 px trunca. Selado PARCIAL por isso."

duration: ~75 min
completed: 2026-08-28
status: halted
---

# Phase 1 Plan 3: As respostas do spike, e a medição que derruba a âncora — Summary

**As 9 perguntas de campo estão respondidas sobre os 335 frames reais, com um portão que resolve no disco cada um dos 41 frames citados — e a análise achou o que ninguém tinha pedido: a margem da âncora do painel, medida em +0,5372 sobre as fixtures do incidente 27x, é NEGATIVA no campo (−0,0643). O plano para aqui, no portão humano da D-04.**

## ESTADO: PARADO NO PORTÃO HUMANO (por desenho, não por falha)

| Task | O que é | Estado |
|---|---|---|
| 1 | `SPIKE-RESPOSTAS.md` + `tools/conferir_spike_respostas.py` | **COMPLETA**, commitada em `10b3b50` |
| 2 | `checkpoint:human-action` `gate="blocking-human"` — o usuário valida ou corrige | **AGUARDANDO O USUÁRIO** |

A Task 2 é a decisão travada D-04: eu analiso os frames e **proponho**; quem valida é o
usuário. Ela não foi executada, simulada nem contornada. `status: halted` no frontmatter é
deliberado e mecânico: o `01-04` declara `depends_on` deste plano, então enquanto este
resumo não disser `complete` o `01-04` não é oferecido ao executor. É a D-04 virando
trava, em vez de recomendação.

## Performance

- **Duração:** ~75 min
- **Tasks:** 1 de 2 (a segunda é o portão humano)
- **Arquivos criados:** 2
- **Suíte:** 1282 passed, 4 failed, 6 skipped — as 4 falhas são as conhecidas de
  `tests/test_agenda.py::TestRegistroEmDisco` (datas fixas em 2026-08-24, janela de poda de
  3 dias vencida), **pré-existentes e fora do escopo deste plano**. Zero regressões: este
  plano não toca uma linha de código de runtime.

## Accomplishments

- **As 9 perguntas respondidas com selo e frame.** 6 `VERIFICADO`, 2 `PARCIAL`,
  1 `NAO RESPONDIDO`. 41 caminhos citados, 41 resolvidos no disco.
- **A pergunta A1 está fechada com número.** O painel percorre **827 × 831 px** numa janela
  de 1720 × 1392, em **34 posições distintas** ao longo das 8 sessões. O 01-02 já sabia que
  ele andava (181 px); o campo mostra que aquilo era o piso. Busca em faixa está descartada
  junto com o retângulo fixo.
- **A âncora do painel não sobrevive ao campo, e isso foi descoberto agora e não na Fase 4.**
  Ver a seção dedicada abaixo.
- **A D-05 está validada com o custo de errar medido.** Um único frame mostra o mesmo item
  base em `+0/+2/+4/+5/+6/+7` valendo de **7,02 a 100,00** na mesma página, no mesmo
  segundo. Misturar variantes não adiciona ruído a uma série: destrói a série.
- **O portão tem dentes, e as três provas de vermelho estão registradas** — inclusive a que
  encontrou um bug real no próprio portão (deviation #1).

## O ACHADO QUE MUDA O 01-04: a margem de campo é NEGATIVA

O 01-02 mediu a âncora contra as fixtures resgatadas do incidente 27x e encontrou margem
**+0,5372**, com o limiar `CASAMENTO_MINIMO_DA_ANCORA = 0,73` posto no meio dela. Aquela
medição está correta para aquele material. O material de campo é outro.

Rodei o molde da âncora nos 335 frames e classifiquei todo frame abaixo de 0,73 com um
**juiz independente da própria âncora**: manchas de arte opaca do painel (borda esquerda,
borda inferior, canto superior esquerdo, início da faixa de abas) na posição conhecida,
aceitando a **melhor** delas — porque uma tooltip é um retângulo local e não cobre o painel
inteiro.

```
pior POSITIVO REAL   0.4110   painel ABERTO, tooltip por cima da faixa de título
melhor NEGATIVO REAL 0.4753   painel FECHADO, sessão mercado-fechado (33 frames)
MARGEM DE CAMPO     -0.0643

o 01-02 media          +0.5372   sobre as fixtures do incidente 27x
```

**As duas classes se sobrepõem.** Não é o valor 0,73 que está errado: é a ideia de que um
único retângulo de título resolve. **19 frames com o painel comprovadamente aberto ficam
abaixo do limiar.** Os dois piores foram conferidos a olho, para que a conclusão não
dependesse só do juiz automático:

| Frame | Âncora | Manchas de arte | O que a inspeção visual mostra |
|---|---:|---:|---|
| `recordings/20260828-055323-mercado-scroll/frame_000084.png` | 0,4110 | 1,000 | painel inteiro na tela; tooltip cobre a metade esquerda do título |
| `recordings/20260828-055323-mercado-scroll/frame_000088.png` | 0,4796 | 1,000 | painel aberto; tooltip de "Common Samurai Doll" sobre o título |

Isto contradiz, com medição, uma decisão registrada no 01-02: *"a âncora é a faixa de
TÍTULO, não a linha de cabeçalhos de coluna: tooltip e marcação de alvo caem sobre as
LINHAS"*. A **marcação de alvo** de fato cai sobre as linhas — em 47 frames do cenário
dedicado ela nunca alcançou o título, e a âncora ficou em 0,9997. A **tooltip** cai onde o
cursor estiver, inclusive sobre o título. A escolha do título continua melhor que a do
cabeçalho de colunas; ela só não é imune.

**Proposta para o 01-04, e ela sai de graça:** o juiz que classificou 19 de 19 corretamente
neste plano é a arquitetura que a detecção precisa — confirmar o painel por manchas de arte
opaca, aceitando a melhor. Nenhum código novo de visão é necessário além do que
`mercado_visao.casamento_da_ancora` já faz.

## Tabela final de selos

| # | Pergunta | Selo | Frames |
|---|---|---|---:|
| 1 | Linhas por página e aparência do slot vazio | VERIFICADO | 4 |
| 2 | Separador de milhar, casas decimais e moeda | VERIFICADO | 4 |
| 3 | Colunas da grade e sua ordem | VERIFICADO | 5 |
| 4 | Preço total e preço unitário | VERIFICADO | 3 |
| 5 | Preço médio embutido: onde fica? | PARCIAL | 2 |
| 6 | A idade do anúncio é exibida? | NAO RESPONDIDO | 2 |
| 7 | Renderização do encanto (D-05) | PARCIAL | 3 |
| 8 | **Posição do painel: fixa ou arrastável? (A1)** | VERIFICADO | 7 |
| 9 | Opacidade (A5) e o que tooltip e alvo cobrem | VERIFICADO | 7 |

**Os dois selos fracos, e por quê:**

- **5 é PARCIAL** porque preço **médio** não existe em nenhum dos 335 frames. O que existe
  é `Minimal price (per unit)` na tela de busca — um **mínimo**, e **inteiro** (perde as
  duas casas decimais). Um mínimo é dominado por um único anúncio barato.
- **7 é PARCIAL** porque a metade da pergunta que a D-05 depende está confirmada (o prefixo
  `+N `, e o item sem encanto não escreve `+0`), e a outra metade não apareceu: **nenhum
  nome truncado nos 335 frames**. A área de texto da coluna `Goods` mede 263 px e o nome
  legítimo mais longo (`Common Mafia Leader Luciano Doll`) usa ~168 px.
- **6 é NAO RESPONDIDO** porque nenhum dos três layouts tem coluna de tempo, mas as 8
  sessões nunca abriram a tela de detalhe/confirmação de compra — ausência em três
  listagens não é prova de ausência no sistema.

## As respostas que o 01-04 lê antes de calibrar

1. **Não existe "a grade": são três layouts de coluna.**
   `Goods | Quantity | Total | Unit price | Buy` (negociação);
   `Auction List | Total Price | 5 mln increment | Buy` (aba Adena);
   `Goods | Minimal price (per unit) | Auction List | Search` (busca).
   A aba Adena, que é a que interessa para preçar adena, **não tem nenhuma das quatro
   primeiras colunas com o mesmo nome**.
2. **A vírgula é milhar E decimal, às vezes na mesma linha:** `5,000,000 Adena` ao lado de
   `62,00 XM Coin`. A desambiguação vem do **sufixo**, não do número. Nenhum ponto apareceu
   como separador em 335 frames.
3. **10 linhas por página na grade de negociação, passo de 45 px exatos; 9 na tela de
   busca** (a caixa de busca come uma). Slot vazio é faixa lisa, sem ícone e sem texto,
   mantendo a listra alternada — "linha vazia" não pode ser decidida por cor de fundo.
4. **O unitário exibido é arredondado a 2 casas** (40,00 ÷ 48 aparece como `0,83`) e não
   reconstrói o total. O banco guarda `Total` e `Quantity`.
5. **O painel é opaco, medido:** o retângulo da âncora é **bit a bit idêntico** (diferença
   máxima 0) em 9 frames consecutivos enquanto o mundo fora dele variava até 255. A
   suposição A5 está confirmada para o título e o corpo da grade; o banner decorativo do
   topo varia 13–20 e por isso não serve de âncora.
6. **A lista rola em saltos, não suavemente.** Dois frames consecutivos durante rolagem
   contínua têm conteúdo completamente diferente e ambos estão **nítidos e alinhados ao
   mesmo grid**. Não existe meia-linha para detectar: o estabilizador da Fase 2 tem que
   comparar frames consecutivos entre si, não procurar uma página "rasgada".

## Task Commits

1. **Task 1: SPIKE-RESPOSTAS.md + o portão que resolve a evidência** — `10b3b50` (feat)

_Task 2 é o portão humano; não gera commit até o "validado" do usuário._

## Files Created/Modified

- `.planning/.../SPIKE-RESPOSTAS.md` — 9 seções numeradas com selo e citação, mais a seção
  "Impacto no planejamento das Fases 2, 3 e 4" com 10 consequências
- `tools/conferir_spike_respostas.py` — portão: 9 seções numeradas de 1 a 9, exatamente um
  selo por seção, pelo menos um frame por selo positivo, e **todo** caminho citado resolvido
  no disco com `Path.exists()`. `--documento` e `--raiz` para ser testável.

## Decisions Made

- **`--raiz` no portão, pelo mesmo motivo de `--pasta-base` no portão irmão.**
  `recordings/` é gitignored e não se materializa dentro de um git worktree — sem a flag, o
  portão seria improvável de rodar exatamente onde a análise é feita.
- **O portão tolera `NAO RESPONDIDO` com til.** O usuário vai **editar** este documento na
  Task 2; um portão que reprovasse por causa de um acento estaria punindo a correção que a
  D-04 pede.
- **Rebaixar uma seção para `NAO RESPONDIDO` sem apagar as citações continua passando.**
  Manter o frame ao lado da resposta rebaixada é informação útil, não erro.
- **Os selos são contados só dentro das seções numeradas.** A legenda tem as três palavras
  e satisfaria o portão sem responder nada — a mutação C prova que ela não repõe uma seção
  perdida.
- **`status: halted`, não `complete`.** É o que trava mecanicamente o `01-04` até o
  "validado".

## Deviations from Plan

### 1. [Rule 1 - Bug] O portão partia a própria seção 8 num `###`, e a mutação achou

- **Found during:** Task 1, na prova de vermelho da mutação A
- **Issue:** A primeira versão encerrava a seção corrente em **qualquer** cabeçalho. A
  resposta 8 tem duas sub-seções `###`, então tudo depois do primeiro `###` deixava de
  pertencer à seção 8. A mutação A plantou um caminho inventado dentro da seção 8 e o
  portão reprovou — mas com a mensagem errada: *"caminho citado FORA das seções
  conferidas"*. O veredito estava certo por acaso; a atribuição, não.
- **Por que isso era grave e não cosmético:** uma resposta cujo **selo** viesse depois de um
  `###` seria acusada de não ter selo, e uma cujas únicas **citações** viessem depois de um
  `###` seria acusada de não ter evidência. Duas reprovações **falsas**, num portão cujo
  valor inteiro é a confiança no veredito. Na prática, a seção 8 estava sendo conferida com
  4 dos seus 7 frames.
- **Fix:** uma seção numerada só é fechada por um cabeçalho de nível **igual ou mais alto**
  que o dela. Um `###` dentro de uma resposta `##` é sub-estrutura da resposta. A legenda e
  a seção "Impacto" continuam de fora porque são `##`, o mesmo nível das respostas.
- **Verification:** com o conserto, a seção 8 passou de 4 para **7** frames confirmados, e a
  mutação A passou a acusar `secao 8` nominalmente.
- **Files:** `tools/conferir_spike_respostas.py`
- **Committed in:** `10b3b50`

### 2. [Rule 1 - Bug] A primeira medição de truncamento mediu uma tooltip

- **Found during:** Task 1, ao responder a pergunta 7
- **Issue:** A varredura automática do "pixel de texto mais à direita da coluna `Goods`"
  devolveu **262 de 263 px — folga de 1 px**, que seria a resposta "o jogo trunca". Recortei
  o frame vencedor para conferir e o vencedor era uma **tooltip** por cima da coluna, não um
  nome.
- **Fix:** gerar os 12 maiores candidatos e conferir um a um a olho, em vez de confiar no
  máximo. Todos os 262 px estavam contaminados por sobreposição; o nome legítimo mais longo
  (`Common Mafia Leader Luciano Doll`) usa ~168 px e termina limpo.
- **Consequência na resposta:** a seção 7 foi selada **PARCIAL** em vez de VERIFICADO, e diz
  o que faltou gravar. Sem esta conferência eu teria selado com confiança uma resposta
  errada — exatamente a classe de erro que esta fase existe para impedir.
- **Registrado dentro do próprio `SPIKE-RESPOSTAS.md`**, porque é o modo de falha de
  qualquer medição futura sobre este material.
- **Files:** `SPIKE-RESPOSTAS.md` (seção 7)
- **Committed in:** `10b3b50`

### 3. [Rule 2 - Missing Critical] O juiz da versão 1 compartilhava a oclusão com o réu

- **Found during:** Task 1, ao classificar os frames sub-limiar
- **Issue:** Para decidir "o painel está aberto?" sem usar a âncora, a primeira versão
  comparava só a **faixa de abas**. Ela reportou **1** falso negativo. Mas nos frames 4–12
  do `mercado-aberto` as abas estão visivelmente na tela e a correlação deu 0,3759 — porque
  a **mesma tooltip** que derruba a âncora também cobre o meio da faixa de abas. Um juiz que
  compartilha a oclusão com o réu não é juiz, e este estava prestes a me fazer subestimar o
  problema em 19×.
- **Fix:** várias manchas de arte opaca espalhadas pelo painel, aceitando a **melhor**. O
  princípio, e não o número, é o que justifica: uma tooltip é um retângulo **local** perto
  do cursor; ela não cobre o painel inteiro, então basta uma mancha limpa. Contagem correta:
  **19** falsos negativos.
- **Verification:** os dois piores foram conferidos visualmente e confirmam o veredito do
  juiz; os 26 classificados como negativo verdadeiro marcaram no máximo 0,387 de mancha.
- **Files:** `SPIKE-RESPOSTAS.md` (seções 8 e 9, e a nota de método no topo)
- **Committed in:** `10b3b50`

### 4. [Rule 1 - Bug] A seção 5 tinha dois selos, e o portão pegou

- **Found during:** Task 1, na primeira execução do portão contra o documento real
- **Issue:** A prosa da seção 5 explicava *"o selo é PARCIAL porque…"*, o que dava dois
  `PARCIAL` na mesma seção. O portão reprovou com `secao 5 (linha 188) tem 2 selos`.
- **Fix:** a frase passou a dizer "o selo acima é o mais fraco de propósito". O portão pegou
  um defeito real do documento na sua primeira execução útil, que é o argumento de escrevê-lo
  **antes** do documento.
- **Files:** `SPIKE-RESPOSTAS.md` (seção 5)
- **Committed in:** `10b3b50`

### 5. [Rule 3 - Blocking] `recordings/` não existe dentro do worktree

- **Found during:** Task 1, na avaliação da `<precondition>`
- **Issue:** A precondição pede as 8 pastas em `recordings/` com `observacoes.jsonl` não
  vazio. Este plano rodou num git worktree, e worktree **não materializa arquivo
  gitignored** — a mesma pedra que o 01-02 registrou na deviation #5 dele.
- **Fix:** as 8 pastas **existem no disco** no checkout principal, que é o fato que a
  precondição afirma; conferi as 8 com `observacoes.jsonl` não vazio (33, 21, 94, 35, 39,
  47, 39, 27 linhas, batendo com a contagem de PNGs) antes de começar. A leitura foi
  **somente leitura**; nada foi escrito, movido ou apagado em `recordings/`.
- **Consequência permanente e desejada:** `tools/conferir_spike_respostas.py` nasceu com
  `--raiz`, seguindo o precedente de `--pasta-base` em
  `tools/conferir_gravacoes_do_spike.py`. Sem a flag, o padrão funciona na máquina do
  usuário; com ela, o portão roda de dentro do worktree.

---

**Total deviations:** 5 auto-corrigidas (3 bugs, 1 missing critical, 1 blocking)
**Impact:** Nenhum item do plano foi reduzido, adiado ou simplificado. As deviations 2 e 3
são o retorno direto da disciplina de evidência desta fase: **duas medições automáticas
mentiram**, uma teria produzido uma resposta selada errada e a outra teria subestimado o
problema da âncora em 19×, e as duas foram pegas por conferir a olho o que o número dizia.
A deviation 1 foi encontrada pela prova de vermelho do próprio portão.

## Issues Encountered

- **Existem DUAS pastas `-mercado-aberto`** em `recordings/` (`20260828-053105` e
  `20260828-063752`). Usei a **mais recente**, que é a regra que
  `tools/conferir_gravacoes_do_spike.py` já aplica (`candidatas[-1]`) e o que o
  `ROTEIRO-SPIKE.md` instrui quando um cenário é regravado. Registrado para que ninguém
  cite a pasta antiga achando que é a mesma evidência.
- **A aba Adena aparece na sessão `mercado-scroll`, não na `mercado-aberto`.** O roteiro
  pedia as duas abas no cenário 2, e a sessão mais recente desse rótulo ficou toda em
  Equipment. O material da aba Adena existe e é bom — só está em outra pasta. As respostas
  citam onde ele realmente está.
- **O `ruff format` não é portão neste repositório:** 19 dos 27 arquivos existentes também
  seriam reformatados. `ruff check` passa limpo no arquivo novo, que é o critério que o
  01-02 já usava.

## Known Stubs

Nenhum. Nada nesta entrega devolve valor fixo ou placeholder. Todo número publicado no
`SPIKE-RESPOSTAS.md` foi medido sobre frames que existem no disco, e o único lugar onde uma
resposta é omitida é onde ela está explicitamente selada `NAO RESPONDIDO` ou `PARCIAL`,
dizendo o que faltou gravar.

## Threat Flags

Nenhuma superfície nova além do `<threat_model>` do plano.

| Ameaça | Estado |
|---|---|
| T-03-01 Repudiation no selo de evidência | **MITIGADA** — o portão resolve os 41 caminhos com `Path.exists()`, exige ao menos um frame por selo positivo, e conta selos só dentro das 9 seções numeradas. Prova de vermelho nas três frentes |
| T-03-02 Tampering: respostas consumidas sem validação humana | **ATIVA POR DESENHO** — a Task 2 (`gate="blocking-human"`) não foi executada nem contornada, e `status: halted` trava o `01-04` mecanicamente |
| T-03-03 Information Disclosure nos caminhos citados | **MITIGADA** — só caminhos entram no documento; zero PNG commitado, conferido no `git status` (só os 2 arquivos do plano) |
| T-03-04 DoS sobre caminho hostil | **MITIGADA** — o portão só chama `Path.exists()`; não abre, não decodifica e não executa nada |
| T-03-SC Tampering na árvore de dependências | **VAZIA por construção** — zero instalações; `requirements.txt` byte-idêntico |

## User Setup Required

Nenhum serviço externo. O que falta é a **sua leitura** — ver o checkpoint abaixo.

## Next Phase Readiness

**Bloqueado no portão humano, e é onde deve estar.**

O `01-04` tem tudo de que precisa **menos** a sua validação:

- a forma da âncora está decidida pela resposta 8, e ela **muda** o que o 01-04 ia
  construir: não é retângulo fixo, não é busca em faixa, e o limiar sozinho não separa as
  classes;
- a grade, os glifos e a convenção de vírgula saem das respostas 1, 2, 3 e 4 — e a resposta
  3 diz que `mercado_grade` precisa gravar **qual** dos três layouts está lendo;
- o recorte dos templates de encanto sai da resposta 7, com a ressalva do truncamento em
  aberto;
- a divergência de 2 px na largura da party window, registrada pelo 01-02, continua de pé
  para quem for derivar recortes de party dos frames de janela.

**Duas perguntas ficam devendo material, e as duas custam ~1 minuto de gravação:** a tela de
detalhe/confirmação de compra (fecha a seção 6) e um item de nome longo com prefixo de
encanto (fecha a seção 7).

## Self-Check: PASSED

- **Arquivos conferidos no disco:** `SPIKE-RESPOSTAS.md`, `tools/conferir_spike_respostas.py`,
  `01-03-SUMMARY.md` — todos FOUND
- **Commit conferido em `git log`:** `10b3b50` — FOUND
- **`<acceptance_criteria>` da Task 1: 6 de 6 verdes**
  1. `python tools/conferir_spike_respostas.py` sai com 0 e imprime as 9 seções com selo e
     contagem ✅
  2. Reprova com caminho inventado (mutação A) → exit 1 nomeando `secao 8` e o caminho ✅
  3. Reprova selo positivo sem frame (mutação B) → exit 1 nomeando seção e linha ✅
  4. A legenda NÃO conta como seção de resposta (mutação C: caiu para 8, não voltou a 9) ✅
  5. Exatamente 9 seções numeradas mais a seção de impacto ✅
  6. A pergunta A1 tem resposta explícita, com alcance medido e frame em cada extremo ✅
- **`<verification>` do plano:**
  1. `python tools/conferir_spike_respostas.py` → **exit 0**, 41 caminhos resolvidos ✅
  2. O portão reprova documento com caminho inventado → provado por mutação ✅
  3. O usuário respondeu "validado" → **PENDENTE, por desenho** — é a Task 2
  4. `python -m pytest tests/ -q` → **1282 passed, 4 failed, 6 skipped**; as 4 falhas são as
     pré-existentes de `test_agenda.py`, zero regressões ✅
  5. Nenhum PNG de `recordings/` commitado → `git show --stat 10b3b50` traz só os 2 arquivos
     do plano ✅
- **Proibições conferidas:** `l2scanner/visao.py` e `l2scanner/rastreador.py` fora do diff;
  `recordings/` intocado (só leitura); `STATE.md` e `ROADMAP.md` não modificados.

---
*Phase: 01-funda-o-firewall-gravador-e-spike-de-campo (workstream mercado)*
*Parado na Task 2 — `checkpoint:human-action`, `gate="blocking-human"`, decisão D-04*
*Date: 2026-08-28*
