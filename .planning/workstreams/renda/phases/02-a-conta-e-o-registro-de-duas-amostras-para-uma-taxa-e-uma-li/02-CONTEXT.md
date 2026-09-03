# Phase 2: A conta e o registro — Context

**Gathered:** 2026-09-02
**Status:** Ready for planning
**Mode:** Áreas cinzentas decididas pelo agente, com a alternativa de cada uma registrada. O
usuário aprovou seguir para a Fase 2 ("Simm!") depois de ver o XP absoluto sair pela primeira vez.

<domain>
## Phase Boundary

Esta fase transforma **uma sequência de amostras em taxas, e cada amostra aceita em uma linha no
disco** — e nada além disso.

Dentro: a diferença entre amostras, o level up que não vira prejuízo, o gasto que não vira renda
negativa, a janela móvel que se anuncia, o tempo até o nível, a ponte XP↔porcentagem, e o
arquivo append-only em `.renda/`.

Fora, e não por acaso: **nenhum laço ao vivo, nenhum painel, nenhum lançador.** A Fase 2 recebe
amostras por parâmetro e devolve números e linhas. Quem captura em laço é a Fase 3. É a mesma
disciplina que fez a Fase 1 ser verificável: sem laço, tudo é função pura testável em
milissegundos, e uma noite inteira de farm cabe num teste.

</domain>

<decisions>
## Implementation Decisions

### Área 1 — A janela móvel, e o que ela faz na lacuna

- **Janela por TEMPO, não por número de amostras.** "Últimos 10 minutos" é o que o usuário
  entende; "últimas 40 amostras" varia de significado quando a cadência muda ou quando o scanner
  fica cego. E a Fase 3 vai ter cadência variável por natureza (o OCR custa dezenas de ms e o
  jogo às vezes some).
- **O tempo cego SAI do denominador.** Se o scanner ficou 20 minutos sem ler, esses 20 minutos
  não foram farmados *do ponto de vista da medição* — dividir por eles produz uma taxa
  artificialmente baixa que o usuário não tem como distinguir de "o farm piorou". A regra: o
  denominador é a soma dos intervalos **entre amostras consecutivas aceitas**, e um intervalo
  maior que um limiar calibrado é **excluído e contado à parte** como lacuna.
  *Alternativa registrada:* dividir pelo relógio de parede. É o padrão silencioso, é mais simples,
  e é a razão de esta decisão estar escrita — sem escrevê-la, alguém a implementa sem perceber.
- **Toda taxa carrega `n` e a janela que cobriu.** Vem do roadmap e do `--mercado`. Uma taxa de
  40 segundos se anuncia como ruído.
- **Duas taxas, não uma:** a da **janela móvel** (o que está acontecendo agora) e a da **sessão
  inteira** (o que a noite rendeu). Elas respondem perguntas diferentes e o usuário quer as duas.
  Medido hoje: a média de 8h45 deu 226 mil adena/h e a janela curta deu 466 mil/h — a diferença é
  o tempo parado, e apresentar só uma das duas mente por omissão.

### Área 2 — Level up e gasto: os dois deltas negativos

- **Level up (REND-03):** `(100 − anterior) + atual`, e um nível a mais. **A regra só dispara
  quando o nível REALMENTE mudou** — e aqui a Fase 1 deixou uma dívida que esta fase herda: o
  nível é o campo mais frágil dos três. Se o nível vier recusado e o EXP cair, a fase **não pode
  adivinhar**: registra a amostra como descontinuidade nomeada e não computa ganho naquele passo.
  Inventar um level up é pior que perder um.
  *Alternativa registrada:* assumir level up sempre que o EXP cair muito (>50 pp). Mais simples,
  e erra exatamente quando o usuário morre e perde EXP — que também é queda grande.
- **Gasto (REND-04):** queda no contador de adena é **gasto**, registrado à parte, fora da taxa
  de ganho. Ganho bruto = soma dos deltas positivos.
- **Farm × venda:** decidido **marcador explícito, não heurística.** O arquivo carrega a coluna,
  e quem sabe preenche. Hoje ninguém sabe, então ela sai como "indeterminado" — e isso é honesto.
  *Por quê:* o roadmap oferece três caminhos (forma do salto, painel do mercado aberto, marcador).
  Os dois primeiros são inferência por limiar mágico sobre um dado que o consumidor não pode
  auditar. D-02 do projeto: um número exibido tem de ter existido. Uma coluna "indeterminado"
  que o dashboard mostra como indeterminado é melhor que um balde errado com cara de certo.

### Área 3 — A ponte XP↔porcentagem (REND-08)

- **A constante mora no `calibration.json`, por personagem E por nível.** `renda_ponte_de_xp:
  {Faerlina: {67: {xp_por_ponto: 383124, medido_em: ..., n_abates: ..., n_linhas: ...}}}`.
  Por nível porque o custo do nível muda; por personagem porque o multiplicador de XP é do
  personagem (562% na Faerlina).
- **Sem constante para o nível atual, o XP absoluto é DECLARADO INDISPONÍVEL.** Nunca convertido
  com a constante do nível anterior. O painel mostra pontos percentuais e diz por que o absoluto
  não está lá. Mesma disciplina do câmbio XM→BRL no `dashboard`: sem taxa informada, mostra XM e
  diz que o R$ está indisponível.
- **A constante carrega a sua procedência**, não só o valor: quantas linhas de chat, quantos
  abates, que janela. Uma constante medida em 6 minutos e uma medida em 3 horas não valem o
  mesmo, e quem lê tem de conseguir saber qual é qual.
- **Esta fase NÃO mede a constante em laço** — ela a consome. Medir exige ler o chat em
  cadência alta, e isso é ferramenta de calibração (Fase 3 ou tarefa própria), não conta.

### Área 4 — O arquivo em `.renda/`

- **Dialeto do `mercado_registro`, colunas próprias.** `;`, `csv` da stdlib, cabeçalho como
  contrato que desliga alto, append por linha com flush, `ArquivoRecortado` no leitor. A
  refutação do "sem um segundo parser" já está escrita no REG-03 e vai repetida no fonte.
- **Um arquivo por personagem por dia**, na forma que o `.mercado/` e o `.loot/` já usam.
- **Colunas previstas** (o plano ajusta): `carimbo`, `personagem`, `nivel`, `exp_decimos`,
  `adena`, `motivo_da_recusa`, `origem_do_ganho`.
- **As RECUSAS também são gravadas**, com o motivo. Um arquivo que só tem sucessos não permite
  responder "por que a taxa desta hora tem n=12 se o scanner rodou 40 minutos". A taxa de recusa
  é dado, não ruído — a Fase 1 já mediu 21% na adena e 79% no nível.
  *Alternativa registrada:* gravar só as aceitas, arquivo menor e mais limpo. Perde a auditoria.
- **Append-only, nunca podado.** Mesma razão do `.loot/`.

### Área 5 — O relógio

- **Entra por parâmetro, em tudo.** Nenhum `datetime.now()`. Não é estilo: o PC é dual boot e o
  Windows volta ~3h adiantado do Linux, e uma taxa por hora com relógio que pula é lixo
  silencioso. `relogio.py` já resolveu isso.
- **Um salto do relógio para trás entre amostras é DESCONTINUIDADE nomeada**, não um intervalo
  negativo. É o mesmo formato dos outros dois deltas negativos desta fase, e pela mesma razão.

### Claude's Discretion

- Nomes de módulo, função e coluna.
- O tamanho padrão da janela móvel e o limiar de lacuna — devem ser calibrados, não fixos.
- Se a sessão é delimitada por processo ou por lacuna longa.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `l2scanner/renda_leitura.py` — a Fase 1 inteira: `ler_os_tres_campos`, `ValorDaRenda`,
  `ValorDaAdena`, `RecusaDaRenda`, e as três regras de par (`o_exp_andou_para_tras`,
  `o_nivel_andou_para_tras`, `a_adena_saltou_ordem_de_grandeza`, `conferir_o_par`) — **escritas,
  puras, e ainda sem chamador por desenho**. Esta fase é o chamador.
- `l2scanner/mercado_registro.py` — `COLUNAS`, `conferir_o_cabecalho`, `conferir_o_terminador`,
  `ContratoDoArquivoQuebrado`, o append com flush. O dialeto.
- `l2scanner/dashboard_dados.py` — `ArquivoRecortado`, a leitura tolerante a linha parcial, com
  as 22.970 sondagens que a sustentam.
- `l2scanner/relogio.py` — o tempo por parâmetro.
- `l2scanner/loot.py` — o argumento escrito de por que `.loot/` não é podado.

### Established Patterns
- Inteiro escalado em vez de float para tudo que é diferenciado (`total_em_centesimos`,
  e agora `exp` em décimos de milésimo de ponto percentual).
- Recusa nomeada em vez de valor degradado.
- `n` e recência colados em todo número que vai à tela.
- Nada de constante mágica no fonte.

### Integration Points
- `.renda/` — pasta nova, contrato com o workstream `dashboard`, que roda em paralelo.
- `calibration.json` — a ponte de XP entra aqui, e a prova de não-destruição da Fase 1 já
  cobre o caminho.
- **NENHUM arquivo do `dashboard` é editado nesta fase.** O contrato é o arquivo em disco.

</code_context>

<specifics>
## Specific Ideas

- **Os dados de hoje são os casos de teste**, e são reais:
  - level up medido: Faerlina `nível 66, EXP 68,5632%, adena 10.673.628` → `nível 67, EXP
    8,0012%, adena 13.160.684`. Ganho correto: `(100−68,5632)+8,0012 = 39,438` pp.
  - taxas medidas: 6,29 pp/h, 466 mil adena/h, 2,41 milhões XP/h, ~104 abates/min.
  - a diferença entre janela curta e média longa: 466 mil/h contra 226 mil/h.
  - taxa de recusa por campo: adena 21%, nível 79%, EXP 0% (14 amostras).
- A ponte medida: 387 XP/abate ÷ 0,001011 pp/abate = **383.124 XP por ponto percentual**,
  nível 67 da Faerlina, 6 minutos, 240 linhas de chat, 622 abates.

</specifics>

<deferred>
## Deferred Ideas

- A **ferramenta que mede a ponte** (ler o chat em cadência alta e calcular a constante). Ela
  existe hoje como script de bancada no scratchpad do agente; virar comando é trabalho da Fase 3
  ou de uma tarefa própria. Esta fase só **consome** a constante.
- SP por hora — mesma linha do chat, mesma ponte, nenhum requisito pede.
- Comparar renda entre locais de farm (REND-07, já em v2).
- Avisar no WhatsApp quando a renda cair (ALER-01, já em v2).

</deferred>

<corrections>
## Resposta às oito contradições da pesquisa (2026-09-02)

Sete são aceitas e vão para o plano. Uma é leitura equivocada e está resolvida aqui.

### C-6 — RESOLVIDA, não é decisão do usuário

A pesquisa leu `01-MEDICOES-DE-CAMPO.md:401` — *"adena 5/10 (50%) aceitas e erradas"* — e
concluiu que as regras de par deixam de ser rede secundária e viram o produto.

**Aquela tabela mede o leitor de OCR, que foi ABANDONADO.** A coluna vizinha diz "quantas por
concordância de 2 escalas": as duas escalas são as duas escalas do **OCR**. É o número que
MATOU o OCR para a adena e virou o LEIT-09 — a adena passou a ser lida por **glifo**. O próprio
`01-02-SUMMARY.md` diz que manteve a adena no censo *"rotulada como caminho abandonado, porque é
o único lugar onde o número que a matou ganha denominador"*.

O leitor que a Fase 2 vai consumir é o de glifo, e ele foi medido separado: **5/5 correto** nas
cinco fixtures pelo caminho de produção, e **11 aceitas de 14 com zero erradas** na amostragem ao
vivo (as 3 restantes foram recusa nomeada). Os 21% do CONTEXT são taxa de RECUSA, não de erro, e
continuam certos.

**O que sobrevive da C-6, e é importante:** o `nível` continua sendo lido por OCR mascarado, e é
nele que 3 das 4 leituras erradas passaram **por concordância** das duas escalas. Isso é atual, é
o LEIT-11, e é exatamente por isso que a Área 2 já decidiu que **um EXP que cai com o nível
recusado não vira level up adivinhado**. O peso das regras de par sobe para o nível — não para a
adena.

### C-1, C-3, C-4, C-5, C-7, C-8 — ACEITAS, e cada uma vira obrigação do plano

- **C-1** — `tests/test_renda_par.py:591-623` varre `l2scanner/*.py` e **proíbe** chamar as regras
  de par. Era a guarda correta enquanto a Fase 1 tinha de provar que não tinha estado. A Fase 2 é
  o chamador legítimo, então **inverter esse teste é a primeira tarefa**, com a razão escrita —
  não apagá-lo: ele passa a exigir que o chamador exista e seja só um.
- **C-3** — a dedup do `mercado_registro` **não é dialeto, é regra de negócio do mercado**, e
  copiá-la apagaria linhas repetidas que aqui são o denominador da taxa. Copiar
  `conferir_o_terminador` (que não conhece coluna nenhuma); **não** copiar `conferir_o_cabecalho`
  (fecha sobre o `COLUNAS` global) nem a dedup.
- **C-4** — `.renda/` **não está no `.gitignore`**. Acrescentar é tarefa, não detalhe: sem isso a
  primeira noite de farm entra num commit.
- **C-5** — "um arquivo por dia como o `.mercado/` e o `.loot/` já fazem" era suposição minha e
  **nenhum dos dois faz isso**. O plano decide a forma pelo que existe, e escreve o motivo.
- **C-7** — REG-02 ("reiniciar não inventa nem apaga renda") não vem do índice em memória; vem da
  conta tratar a primeira amostra pós-reinício como **âncora**. Não há peça de disco a copiar.
- **C-8** — `renda_ponte_de_xp` terminaria a fase **vazia**, e o caminho "XP absoluto disponível"
  nunca seria exercido com dado real. O plano **semeia a constante medida** (Faerlina, nível 67,
  388.700 XP/pp, com a procedência: 55 Hz, censo completo, 114 abates, 240 linhas de chat) como
  o primeiro registro, e testa os dois caminhos — com e sem constante.

### C-2 — ACEITA, e ela já tinha sido corrigida uma vez

"O dashboard acrescenta uma lista de colunas, não um parser" é falso, e a pesquisa foi mais longe
que a correção que já estava no REG-03: seguiu a cadeia até `dashboard_dados.py:454`, que chama o
parser do mercado **pelo nome** e confere contra o `COLUNAS` global. O plano escreve a refutação
no fonte e **não promete** ao `dashboard` nada além de um arquivo em disco no mesmo dialeto.

</corrections>
