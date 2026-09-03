# Requisitos — v1-renda

**Workstream:** renda
**Milestone:** v1-renda — quanto rende esta hora, e quanto falta para o nível
**Criado:** 2026-09-02, a partir do pedido do usuário + spike de campo na tela ao vivo

> **Fonte de dados: a BARRA INFERIOR do cliente, não o chat.** O usuário pediu para ler os
> números que sobem no chat e ele mesmo levantou a ressalva ("eles sobem bem rápido"). O spike
> `.planning/spikes/renda-barra-inferior.md`, feito na tela dele antes deste documento, mostrou
> que a barra de status já exibe **EXP 68,5632%**, o **total de adena** e, sob o retrato, o
> **nível** — permanentemente, sem rolagem, em texto branco de alto contraste. Ler a barra é uma
> **diferença entre duas amostras**; ler o chat é uma **soma de eventos**, e numa soma toda linha
> perdida é renda perdida para sempre. O chat fica registrado como enriquecimento de v2.

> **Este workstream não desenha tela de navegador.** Ele produz o dado e o registro. O dashboard
> web é o workstream `dashboard`, rodando em paralelo. O contrato entre os dois é um arquivo.

## Fase 1 — a leitura: transformar pixel em número, ou recusar

- [ ] **LEIT-01**: O scanner lê o **nível** do personagem (o número sob o retrato). Medido no
      spike: o recorte cru devolve vazio porque o número fica sobre a arte do retrato; com
      máscara de branco `inRange(HSV, (0,0,vmin), (179,70,255))` a leitura sobe de vazio
      (vmin=170) para `6b` (190) para `66` (210). O `vmin` é **calibrado, nunca constante no
      fonte** — é exatamente o tipo de limiar que o CLAUDE.md deste projeto proíbe fixar.

- [ ] **LEIT-02**: O scanner lê o **EXP em porcentagem com as quatro casas decimais**
      (`68,5632%`). As quatro casas não são luxo: elas são o que torna a taxa mensurável em
      minutos em vez de horas. Uma leitura que perca as decimais é **recusada**, não arredondada.

- [ ] **LEIT-03**: O scanner lê o **total de adena** (`10.673.628`). Medido no spike: o Windows
      OCR já no projeto (`l2scanner.ocr`) devolve `Special 58,40 13,091 10,679,769` sobre o
      recorte cru da direita da barra, sem pré-processamento nenhum.

      **Correção medida em 2026-09-02, duas vezes, e a segunda derruba o leitor inteiro.** A
      primeira metade da frase acima — *"sobre o recorte cru"* — caiu com o LEIT-08: com o fundo
      atrás da barra semitransparente em grama clara, o cru devolve `''` nas duas escalas. A
      segunda metade — *"o Windows OCR devolve a adena"* — caiu com o **LEIT-09**: medido, o OCR
      sobre este recorte aceita número **errado** e nenhuma regra de cruzamento entre escalas
      conserta isso. **A adena é lida por glifo, não por OCR.** O requisito continua sendo o
      mesmo — ler o total de adena —; o que mudou é o leitor, e o argumento inteiro está no
      LEIT-09. A frase original fica escrita aqui porque um número que caiu precisa dizer que
      caiu.

- [ ] **LEIT-04**: **Leitura duvidosa vira recusa, não número.** Um EXP que ande para trás sem
      level up, uma adena que salte ordens de grandeza, um campo que volte vazio — nada disso
      entra no registro. O modo de falha que este requisito existe para impedir é o pior
      possível para um medidor: um número errado é indistinguível de um número certo depois de
      gravado, e envenena toda taxa calculada dali para a frente.

- [ ] **LEIT-05**: **Todas as regiões e todos os limiares moram no `calibration.json`.** As
      coordenadas medidas no spike (`0,1368 500x26` para a esquerda da barra; `1230,1368 470x26`
      para a direita; `246,736 30x20` para o nível) valem para a janela do usuário HOJE. Elas são
      ponto de partida do calibrador, não constante do produto — mover a janela não pode custar
      um commit.

- [ ] **LEIT-07**: **A calibração da renda é POR PERSONAGEM.** *(Acrescentado em 2026-09-02, a
      partir de `01-MEDICOES-DE-CAMPO.md`, achado M-F.)* Medido com as duas instâncias vivas: a
      janela de status da Faerlina põe o nível em `246,736` e a da Yazalaque em `236,750` — 14
      px de diferença na vertical, porque o usuário posicionou a UI de cada cliente à mão. Um
      retângulo único lê o nível certo de uma e **lixo da outra**, e o lixo aqui é o pior caso
      possível: a região vizinha mostra outro número (`349` na Yazalaque, `112` na Faerlina) que
      passaria em `numero_valido` sem reclamar. Os pisos de brilho seguem junto: o nível da
      Faerlina lê em 190–220 e o da Yazalaque em 170–210.

- [ ] **LEIT-08**: **Não existe um piso de brilho único, e a adena exige máscara.** *(M-E.)* As
      bandas úteis do nível (190+) e da adena (150) **não têm interseção** — um campo único é
      impossível, cada região tem o seu. E o recorte cru da adena devolve `''` nas duas escalas
      quando o fundo atrás da barra semitransparente é claro: a premissa do LEIT-03 ("o OCR já
      devolve a adena do recorte cru") veio do spike, onde o fundo estava escuro, e é **falsa no
      caso geral**. Pior: a banda útil da adena da Faerlina tem **largura 1** (só `vmin=150`).
      Isso não é margem, é sorte — e o calibrador tem que reportar a largura da banda e avisar
      quando ela for estreita, não só gravar o valor.

- [ ] **LEIT-09**: **A adena é lida por GLIFO, os moldes dessa fonte são construídos pelo
      calibrador, e um conjunto incompleto RECUSA em vez de adivinhar.** *(Acrescentado em
      2026-09-02 a partir do "Adendo" de `01-MEDICOES-DE-CAMPO.md`, achados M-G a M-J.)* São três
      cláusulas e cada uma tem número:

      1. **O OCR não serve para este campo.** A regra "uma leitura válida + uma abstenção →
         aceita" (LEIT-04 via M-D) aceita valor errado em dado real: no piso 150 a Yazalaque lê
         `106.020` contra a verdade `1.696.020`, e no piso 160 a Faerlina lê `91` contra
         `13.160.684`. Os dois passam em `numero_valido` — são gramaticalmente válidos,
         plausíveis, e errados por seis ordens de grandeza (M-G). Apertar a regra para "as duas
         escalas têm de concordar" também não salva: em busca exaustiva a Faerlina produziu
         **173 concordâncias e as 173 estão erradas**, todas lendo `13091`, que é a **L-Coin**
         (M-H). Concordância prova que as duas escalas leram a mesma coisa, e a mesma coisa pode
         ser o campo do lado. A adena é o único campo desta fase com um **sósia gramatical
         adjacente**, e é por isso que só ela sai do OCR — o EXP fica, porque lê numa banda larga
         (130–170) e a gramática dele (`\d+[.,]\d{4}%`) não colide com vizinho nenhum.

      2. **Os moldes do mercado não transferem, e a diferença é geométrica.** A fonte da barra tem
         glifo de **5 px de largura por 10 de altura**, e a vírgula tem 2 de largura — invariável
         nas duas instâncias e em todo piso varrido (**M-K**); os 13 moldes de
         `mercado_templates_de_digito` são **4x9** (M-I). **O "17 px" que esta cláusula afirmava
         está REFUTADO, e fica escrito onde estava:** o M-I mediu a faixa sobre um recorte da adena
         que continha os **ícones de moeda das duas pontas**, e `segmentar_glifos` devolve UMA
         faixa para o retângulo inteiro — o ícone, mais alto que o dígito, empurrou o topo e a
         base. A medição limpa, sobre a L-Coin **sem ícone**, deu **altura 10** nas duas
         instâncias. O veredicto do M-I sobrevive inteiro — os moldes do mercado continuam sem
         transferir —, mas a distância é de **um pixel em cada eixo**, e não de 9 contra 17. E a
         correção é operacional e não editorial: **uma guarda de altura escrita contra 17 recusaria
         todo molde legítimo desta barra**, e o modo de falha seria um cortador que nunca corta
         nada. Casar um dígito de 5x10 contra um molde de 4x9 põe a decisão nas mãos da área vazia
         do alinhamento, que é o
         mesmo argumento com que o próprio repositório proíbe misturar dígitos com palavras na
         mesma matriz. **Construir o conjunto da barra é trabalho novo, e é do cortador de moldes
         do `01-05`** — no
         caminho de `calibrar_mercado.propor_rotulo`: a máquina propõe, o humano confirma. O
         caminho existe porque a segmentação por glifo funciona: em `vmin` 180–190, justamente
         onde o OCR devolve vazio, `segmentar_glifos_no_brilho` devolve
         `[15, 5, 2, 5, 5, 5, 2, 5, 5, 5, 16]` na Yazalaque e oito dígitos na Faerlina — ícone,
         dígitos de largura 5, vírgulas de largura 2, ícone —, batendo com a verdade de campo nas
         duas, e numa banda **larga** em vez da banda de largura 1 do OCR (M-J).

      3. **Conjunto incompleto recusa, e diz o que falta.** A região da adena das duas fixturas dá
         os dígitos **0, 1, 2, 3, 4, 6, 8 e 9**. **O "faltam 5 e 7, que só aparecem com o tempo"
         está REFUTADO pelo M-L, e a refutação fica aqui:** os dois estão na tela **agora**, em
         outros campos da **mesma barra** — o `5` no bônus da Faerlina (`592%`), o `7` no EXP da
         Yazalaque (`76.6646%`) e na L-Coin dela (`9.790`) —, e a largura 5 foi confirmada por
         segmentação no bônus, no EXP, na L-Coin e na adena das duas instâncias: **é uma fonte só
         na barra inteira**. O conjunto 0–9 **fecha com as duas fixturas que já existem**, desde
         que a colheita varra **qualquer campo da barra** e não apenas a região da adena. O
         bloqueio era artefato de restringir a colheita a uma região, e o conserto que a recusa
         anuncia deixou de ser *farmar até o dígito aparecer* e passou a ser *rodar o cortador
         apontando outro campo*. O calibrador
         tem de trabalhar com o conjunto pela metade e **nomear os que faltam** em vez de travar —
         mas a leitura com conjunto incompleto é proibida, e a proibição é medida e não zelosa:
         `conjunto_descreve_numeros` exige `0123456789,` inteiro porque um conjunto pela metade
         **falha aberto** — um `8` sem molde de `8` casa com `0` a 0,7826 contra piso 0,4698, e a
         margem não pega porque a folga sobre o segundo colocado é de 0,1628. Um conjunto pela
         metade não é meia leitura: é a leitura errada com a mesma confiança da certa. Enquanto
         faltar um dígito, a adena **recusa com motivo próprio, dizendo quais faltam** — e essa
         recusa é distinguível de campo vazio e de gramatica inválida, porque o conserto é outro:
         farmar até o dígito aparecer na tela e rodar o calibrador de novo.

- [ ] **LEIT-06**: Existe um **calibrador** para essas regiões, na mesma família do
      `calibrar-mercado.bat` e do `calibrar.bat` que já existem. Sem ele, LEIT-05 é uma promessa
      sem como cumprir.

- [ ] **LEIT-10**: **Um piso de brilho só não sobrevive à mudança de área de farm.** *(M-S,
      medido pela bancada do `01-02`.)* A banda útil do EXP da Faerlina andou de `140..170` para
      `160..180` em 8,5 horas — só porque o cenário atrás da barra semitransparente mudou. As
      duas se tocam em dez unidades. E no frame das 09h30 a adena tem banda de largura **ZERO**
      por OCR em todos os 31 pisos varridos. O modo de falha é cruel com o usuário: ele calibra
      numa área, muda de mapa, e o número para de sair sem que nada tenha quebrado — nem o
      calibrador está errado, nem a leitura.

      **O dono é a Fase 3**, onde existe laço ao vivo: antes de declarar cegueira, o leitor
      tenta os pisos vizinhos da banda gravada e usa o que produzir leitura válida, registrando
      qual usou. Na Fase 1 isso seria estado dentro de uma função que a fase inteira definiu como
      pura. Fica escrito aqui para não virar surpresa lá.

- [ ] **LEIT-11**: **Concordância entre as duas escalas NÃO prova acerto, e o cruzamento não é a
      defesa principal.** *(M-R.)* Medido: **3 das 4** leituras erradas de nível foram aceitas
      **por concordância** das duas escalas — e o nível não tem sósia gramatical ao lado, então a
      explicação do M-H (a L-Coin) era estreita demais. As duas escalas partem do mesmo pixel
      mascarado e não são independentes o bastante para que concordar prove alguma coisa. No EXP
      é pior de outro jeito: nas três leituras erradas a escala 3x leu os **mesmos dígitos
      errados** e abstinha por gramática — a abstenção estava escondendo concordância no erro.

      O cruzamento **fica**: ele pegou 2 casos em 124 (1,6%) no nível, e os dois liam `65` contra
      `69` — `65` é exatamente o valor que a concordância tinha aceitado oito horas antes no mesmo
      personagem. Mas ele é rede secundária. **A defesa principal são as regras de par da Fase
      2**, e este requisito existe para que ninguém confie demais no cruzamento antes delas
      existirem.

- [ ] **REND-08**: **O XP sai em NÚMERO ABSOLUTO, não só em porcentagem — por uma ponte
      calibrada uma vez por nível, e nunca por somar o chat.** *(Acrescentado em 2026-09-02 a
      pedido do usuário: "XP é isso que aparece no chat e sobe a porcentagem, mas preciso do
      número do chat".)*

      **Somar o chat não funciona, e está medido.** Amostrando a 0,8 s, o chat entregou **55,4%**
      da adena que a barra viu no mesmo intervalo (25.766 contra 46.501); a 2,0 s entregou
      **29,8%**. O chat tem **6 linhas visíveis** e o personagem abate ~104 mobs/min, então a
      janela inteira vira em ~4 s. Somar linhas produziria um XP/h **45% abaixo da verdade, com
      cara de medido** — que é o modo de falha que este workstream inteiro existe para impedir.

      **A ponte é uma constante por nível:** `XP por ponto percentual = XP por abate ÷ pp por
      abate`. Medida na Faerlina, nível 67, em 6 minutos:

      | grandeza | valor | de onde veio |
      |---|---|---|
      | XP por abate | 387 (média de 240 linhas) | chat — **não precisa ser completo**, só representativo |
      | pp por abate | 0,001011 | **barra** — degraus do EXP, 199 saltos de ~10 unidades, 101 de ~20, 33 de ~30 |
      | **XP por ponto percentual** | **383.124** | a razão |
      | **XP total do nível 67** | **38,3 milhões** | ×100 |

      **A divisão de trabalho é o ponto:** o chat entrega o que NÃO exige completude (quanto vale
      um abate); a barra entrega o que exige (quantos abates aconteceram). Invertido, não funciona.

      **Cruzamento independente, e ele fecha:** 371 linhas de adena dão 83,1 por drop; a barra viu
      +46.501 → **559 drops**. O degrau do EXP diz **622 abates**. Razão 0,90, coerente com "nem
      todo abate dropa adena". Se o degrau de ~10 fosse **dois** abates, o EXP diria 311 e a razão
      viraria 1,80 — a adena teria de cair em quase o dobro dos abates existentes, que é
      impossível. É isso que sustenta que o degrau unitário é um abate, e não dois.

      **Refinamento a 55 Hz, 2026-09-02 — e ele valida a Fase 1 de quebra.** A conta acima
      agrupava aglomerados de degraus a 0,8 s de amostragem. Refeita a **0,018 s** (8.555 leituras
      de EXP em 2,5 min), o censo ficou COMPLETO e exato:

      - **zero leituras negativas** em 8.555 — o leitor de EXP da Fase 1 não oscila;
      - **a soma dos 188 degraus é 1903 unidades, e a barra andou exatamente 1903.** Nenhum
        evento escapou. Isto é um censo, não uma amostra.

      Com o censo, o aglomerado do abate isola-se sozinho: **114 eventos de ~10 unidades, média
      9,956**, o que dá `387 ÷ 0,0009956 = 388.700 XP por ponto percentual` e **38,87 milhões no
      nível** — 1,5% acima da primeira conta, que portanto se sustenta.

      **E apareceu um segundo aglomerado que eu não sei explicar:** 50 eventos de ~3 unidades, a
      20 por minuto, somando 7,9% do XP da janela. Eles não são erro de leitura (não há degrau
      negativo nenhum) e não são abate (o chat mostra XP por abate entre 363 e 439, um intervalo
      de 1,2× — não de 3×). Que o abate é o aglomerado de ~10 está estabelecido pelo RITMO: 45,6
      por minuto nesta janela, que rodou a 4,57 pp/h; corrigido para os 6,29 pp/h da janela de 6
      minutos dá 62,8/min, contra os ~58/min que o chat indicou. O aglomerado de ~3 continua sem
      identificação, e **isso não afeta a constante** — ela converte pontos percentuais em XP do
      nível, seja qual for a origem do ganho.

      **A constante é POR NÍVEL** e tem de ser recalibrada a cada level up, porque o custo do
      nível muda. Enquanto ela não existir para o nível atual, o painel mostra pontos percentuais
      e **diz que o XP absoluto está indisponível** — nunca converte com a constante do nível
      anterior.

- [ ] **REND-09**: **A convenção do bônus está resolvida, e por medição.** *(Mesma origem. O
      usuário perguntou se `363 XP (bonus: 299)` é 363 ou 662, e disse não saber.)* **É 363.** O
      valor entre parênteses é a PARTE do total que veio de bônus, não um extra a somar.

      A prova: para cada uma das 11 linhas distintas capturadas, `total ÷ (total − bonus)` cai
      entre **562% e 567%** em dez delas (`363/64 = 5,67`; `388/69 = 5,62`; `405/72 = 5,62`;
      `439/78 = 5,63`) — e a própria barra exibe **562%** ao lado do EXP, que é o multiplicador de
      XP do personagem. Se o total fosse `363+299`, o multiplicador seria 10,3× e nada na tela
      corresponderia a ele. Quem for parsear a linha do chat **não soma o parênteses**, e há teste
      com o par medido prendendo isso.

## Fase 2 — a conta: de duas amostras para uma taxa

> *No `ROADMAP.md` esta seção e a de baixo viraram uma fase só, a **Phase 2**. O motivo
> está lá, em "Por que três fases".*

- [ ] **REND-01**: **XP por minuto e por hora**, em pontos percentuais do nível atual.

- [ ] **REND-02**: **Adena por minuto e por hora.**

- [ ] **REND-03**: **Subir de nível não é renda negativa.** O EXP% zera no level up. A conta é
      `(100 - anterior) + atual`, e um nível a mais. Sem isso, a melhor coisa que acontece numa
      farmada registra o pior número da noite.

- [ ] **REND-04**: **Gastar adena não é renda negativa.** Uma queda no contador é um **gasto**,
      registrado como tal e fora da taxa de ganho. O ganho bruto é a soma dos deltas positivos.
      Vender no mercado entra como ganho — é correto —, mas o registro precisa deixar farm e
      venda distinguíveis, senão a pergunta "quanto rende farmar aqui" fica sem resposta.

- [ ] **REND-05**: **Tempo até o próximo nível**, derivado de `(100 - exp%) / (exp% por hora)`.
      Este é literalmente o "quanto tempo vai levar" que o usuário pediu, e a barra o entrega
      **sem tabela de XP por nível** — que seria uma dependência externa, específica de servidor
      e desatualizável a cada patch.

- [ ] **REND-06**: A taxa é de **janela móvel, e diz de quantas amostras ela veio.** Uma taxa
      calculada sobre 40 segundos de sessão é ruído, e tem que se anunciar como ruído. Mesma
      disciplina de `n` e recência que o `--mercado` já aplica a todo número que vai à tela.

## Fase 3 — o registro: o que o dashboard vai consumir

> *O `ROADMAP.md` fundiu esta seção com a de cima: `REND-*` e `REG-*` são a **Phase 2**.*

- [ ] **REG-01**: Cada amostra aceita vira **uma linha num arquivo append-only** em pasta
      própria (`.renda/`), com carimbo de tempo. Append-only pela mesma razão do `.loot/`:
      "quanto eu rendia mês passado" é pergunta sobre meses, não sobre a semana.

- [ ] **REG-02**: O registro **sobrevive a reinício** do scanner, e reiniciar não inventa nem
      apaga renda: a primeira amostra depois de subir é âncora, não delta.

- [ ] **REG-03**: O formato é **o mesmo contrato que o `dashboard` já sabe ler** do
      `.mercado/observacoes.csv` — leitor somente-leitura, tolerante a linha parcial durante a
      escrita. Um segundo formato exigiria um segundo parser no outro workstream.

      **Correção medida pelo roadmap (2026-09-02):** "sem um segundo parser" é bonito e é
      falso. `dashboard_dados.observacoes_ao_vivo` delega para
      `mercado_registro.observacoes_do_arquivo`, que é **amarrada a `COLUNAS =
      (chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos, quantidade,
      residuo_do_cruzamento)`** — e uma amostra de renda não é uma oferta de mercado. O que se
      reusa, e é o que importa, é o **dialeto** (`;`, `csv` da stdlib, cabeçalho como contrato
      que desliga alto, append por linha com flush) e a **disciplina de falha**
      (`ArquivoRecortado`, recorte na última linha completa durante a escrita, medida em
      22.970 sondagens sobre 200.000 appends). O `dashboard` acrescenta uma lista de colunas,
      não um parser. A refutação vai escrita no fonte.

- [ ] **REG-04**: O registro diz **de qual personagem** é a renda. *(Acrescentado pelo roadmap
      em 2026-09-02 — ver "Premissas assumidas", item 5.)* O usuário roda **duas instâncias**
      lado a lado (Yazalaque e Faerlina) — é a razão de AGEN-07 existir no `PROJECT.md` — e EXP
      e adena são **do personagem**. Um `.renda/` sem essa marca soma a adena de um com o EXP
      do outro e produz uma taxa que não descreve ninguém. Cai exatamente no modo de falha que
      LEIT-04 existe para impedir: renda misturada entre dois personagens não parece errada em
      lugar nenhum — ela só parece baixa. É barato: `--janela` já é exigido pelo `--mercado`
      pelo mesmo motivo, e `cliente.nome_do_personagem` já extrai o nome do título da janela.

## Fase 4 — a tela: o modo `--renda`

> *No `ROADMAP.md` esta é a **Phase 3**.*

- [ ] **CONS-01**: Um **painel ao vivo** no console mostra nível, EXP%, adena, as taxas por
      minuto e por hora, o tempo até o nível, e há quanto tempo a sessão corre. Mesmo
      `rich.Live` das telas que já existem.

- [ ] **CONS-02**: Sobe por **modo próprio** (`--renda`) e lançador próprio, em processo
      separado. Derrubar a renda não derruba a vigilância da party, e vice-versa.

- [ ] **CEGO-01**: Jogo fechado, minimizado ou na tela de login → **pausa declarada**, não
      registro de lixo. O projeto já tem o modo cego resolvido para a party (v1, quatro rodadas
      de correção); esta fase o REUSA, não o reinventa.

- [ ] **CEGO-02**: Valores **bit-idênticos por N amostras** → o scanner diz que está parado em
      vez de afirmar renda zero. Renda zero e cegueira são coisas diferentes, e a diferença
      importa às 4 da manhã.

## v2 — reconhecido, adiado

- **CHAT-01**: XP **absoluto** (`You have acquired 405 XP`) lido do chat, como enriquecimento
  sobre um tronco que já funciona. Só vale a pena se o dashboard pedir o número absoluto; a
  porcentagem já responde "quanto tempo falta".
- **CHAT-02**: SP por hora, mesma fonte.
- **REND-07**: Comparar renda entre locais de farm ("War-Torn Plains rendeu X, o outro rendeu Y").
- **ALER-01**: Avisar no WhatsApp quando a renda cair (morreu, travou, deslogou).

## Fora de escopo

| Item | Razão |
|------|-------|
| Ler o chat como fonte **primária** | Rolagem rápida + dedup + linha perdida = renda perdida para sempre. A barra dá o total, não a soma. Medido, não suposto. |
| Tabela de XP absoluto por nível | Dependência externa, específica de servidor, quebra a cada patch — e a porcentagem já entrega o ETA sem ela. |
| Desenhar o dashboard web | É o workstream `dashboard`, rodando em paralelo. O contrato entre os dois é um arquivo. |
| Qualquer input no jogo | Restrição dura do projeto, e este workstream não tem motivo nenhum para chegar perto dela. |
| Ler memória do processo | Já fora de escopo no PROJECT.md. Repetido aqui para o escopo não voltar por baixo. |

## Rastreabilidade

> **As fases deste documento eram uma sugestão; o `ROADMAP.md` decidiu por três.** `REG-*` foi
> fundido com `REND-*` porque REND-04 ("uma queda no contador é um gasto, **registrado como
> tal**") é um requisito sobre o registro que estava morando na fase da conta, e porque REG-02
> ("a primeira amostra depois de subir é âncora, não delta") é uma regra de taxa vestida de
> persistência. O argumento inteiro está em `ROADMAP.md`, seção "Por que três fases".

| Requisito | Fase | Status |
|-----------|------|--------|
| LEIT-01 | Phase 1 | Pendente |
| LEIT-02 | Phase 1 | Pendente |
| LEIT-03 | Phase 1 | Pendente |
| LEIT-04 | Phase 1 | Pendente |
| LEIT-05 | Phase 1 | Pendente |
| LEIT-06 | Phase 1 | Pendente |
| LEIT-07 | Phase 1 | Pendente |
| LEIT-08 | Phase 1 | Pendente |
| LEIT-09 | Phase 1 | Pendente |
| REND-01 | Phase 2 | Pendente |
| REND-02 | Phase 2 | Pendente |
| REND-03 | Phase 2 | Pendente |
| REND-04 | Phase 2 | Pendente |
| REND-05 | Phase 2 | Pendente |
| REND-06 | Phase 2 | Pendente |
| REG-01 | Phase 2 | Pendente |
| REG-02 | Phase 2 | Pendente |
| REG-03 | Phase 2 | Pendente |
| REG-04 | Phase 2 | Pendente |
| CONS-01 | Phase 3 | Pendente |
| CONS-02 | Phase 3 | Pendente |
| CEGO-01 | Phase 3 | Pendente |
| CEGO-02 | Phase 3 | Pendente |

**Cobertura:** 21 requisitos v1 (17 originais + REG-04 + LEIT-07 + LEIT-08 + LEIT-09), 21
mapeados, 0 sem fase, 0 em duas fases.

**Dono de cada requisito da Fase 1, depois da revisão de 2026-09-02 contra
`01-MEDICOES-DE-CAMPO.md` — o "Adendo" (achados M-G a M-J) e a "Correção ao adendo" (M-K e M-L),
que mandam sobre o Adendo onde os dois se cruzam** — nenhum requisito fica sem plano:

| Requisito | Plano(s) que o fecham |
|---|---|
| LEIT-01 — o nível | `01-04` (o leitor), com o retângulo e o piso vindos do `01-03` |
| LEIT-02 — o EXP com quatro casas | `01-01` |
| LEIT-03 — a adena | `01-04` (o leitor **por glifo**; as duas premissas do texto original — "o cru já lê" e "o OCR devolve a adena" — estão refutadas por LEIT-08 e LEIT-09) |
| LEIT-04 — leitura duvidosa vira recusa | `01-01` (gramática, cruzamento, recorte), `01-02` (a taxa de discordância com denominador), `01-04` (as três regras de par) |
| LEIT-05 — tudo no `calibration.json` | `01-01` (o esquema), `01-03` (o escritor) |
| LEIT-06 — o calibrador | `01-03` |
| LEIT-07 — calibração por personagem | `01-01` (o esquema e a proibição de queda), `01-03` (o calibrador por personagem), `01-04` (a leitura por personagem) |
| LEIT-08 — um piso por região, e a adena exige máscara | `01-01` (o esquema com três pisos), `01-03` (a banda por região e a largura como aviso), `01-04` (a máscara obrigatória na adena) |
| LEIT-09 — a adena por glifo, os moldes da barra, e o conjunto incompleto que recusa | `01-01` (o esquema: `renda_moldes_da_barra` no topo, e o piso **e o retângulo** de glifo na entrada do personagem), `01-03` (a varredura da adena, que passou a classificar pela **forma** das corridas), **`01-05`** (o cortador que **corta** os moldes de **5 px de largura por 10 de altura** e nomeia os que faltam, mais a peneira de forma no módulo puro), `01-04` (o leitor por glifo, o descarte dos ícones por largura, e a recusa nomeada por conjunto incompleto) |

**Duas correções nesta linha do LEIT-09, e ficam escritas em vez de trocadas em silêncio:**

1. **O dono do corte dos moldes é o `01-05`, e não o `01-03`.** Aquela era a Tarefa 4 do `01-03`;
   o plano tinha quatro tarefas e 148k de estimativa, violando a regra de 2-3 tarefas por plano, e
   o corte virou plano próprio na **mesma onda 2**, com a **mesma dependência** (`01-01`) e **zero
   arquivo em comum**. O que sobrou no `01-03` é a consequência para a varredura — a `barra_direita`
   classifica pela forma das corridas —, e não a tipografia.
2. **Os moldes são de 5x10, e nunca de 17 px de altura.** O "17" veio do M-I, que mediu a faixa
   sobre um recorte da adena **contendo os ícones de moeda das duas pontas** — e
   `segmentar_glifos` devolve UMA faixa para o retângulo inteiro, então o ícone, mais alto,
   empurrou o topo e a base. A medição limpa é o **M-K**: sobre a L-Coin sem ícone
   (`1440,1355 90x40`), `faixa = (17, 26)`, **altura 10**, larguras `[5, 5, 2, 5, 5, 5]` → `13.091`,
   e o mesmo nas duas instâncias. **O veredicto do M-I sobrevive** — os 13 moldes de
   `mercado_templates_de_digito` são 4x9 e continuam sem transferir —, mas a distância é de **um
   pixel em cada eixo**. Isto não é correção editorial: uma **guarda de altura escrita contra 17
   recusaria todo molde legítimo desta barra**, e o modo de falha seria um cortador que nunca corta
   nada. Quem escrever a guarda compara contra **10**.

## Premissas assumidas (usuário dormindo)

Estes gates do `/gsd-new-milestone` seriam perguntas. Foram decididos com base no pedido
escrito e no spike, e ficam aqui explícitos para revisão de manhã:

1. **Barra em vez de chat.** O usuário pediu chat com ressalva própria; o spike achou fonte
   melhor. Se ele quiser o XP absoluto mesmo assim, CHAT-01 sobe de v2 para v1 sem jogar nada
   fora — o tronco continua o mesmo.
2. **Pesquisa de projeto (4 agentes) pulada.** O domínio foi resolvido por medição na tela dele,
   não por busca. A pesquisa POR FASE (`workflow.research: true`) continua ligada.
3. **Console primeiro, WhatsApp nunca nesta v1.** Mesma decisão que o `mercado` v1 tomou.
4. **Sem branch nova.** `git.branching_strategy` é `none` neste projeto e o agente do dashboard
   está em outro lugar; seguir a convenção do projeto é mais seguro que inventar uma.
5. **REG-04 acrescentado sem perguntar** (roadmap, 2026-09-02). O registro passa a carregar o
   personagem. Não é ampliação de escopo: é o que impede o arquivo de misturar as duas
   instâncias que você roda ao mesmo tempo. Se você preferir **um arquivo por personagem** em
   vez de uma coluna, é troca de formato dentro da Fase 2 e não muda o roadmap.

---
*Requisitos definidos: 2026-09-02*
