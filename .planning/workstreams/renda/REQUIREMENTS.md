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

- [ ] **LEIT-06**: Existe um **calibrador** para essas regiões, na mesma família do
      `calibrar-mercado.bat` e do `calibrar.bat` que já existem. Sem ele, LEIT-05 é uma promessa
      sem como cumprir.

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

**Cobertura:** 18 requisitos v1 (17 originais + REG-04), 18 mapeados, 0 sem fase, 0 em duas
fases.

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
