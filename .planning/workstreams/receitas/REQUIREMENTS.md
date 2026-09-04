# Requisitos — v1-receitas

**Workstream:** receitas
**Milestone:** v1-receitas — a receita lida da tela, e o custo real de craftar em adena, XM e R$
**Criado:** 2026-09-04, a partir de uma captura da janela **Special Craft** enviada pelo usuário

> **Metade disto já existe e não se reimplementa.** O `mercado` entregou o **ANAL-04**:
> `mercado_analise.margem_de_craft` mais `config.Receita` / `ComponenteDaReceita` /
> `ler_receitas` / `ReceitaInvalida`. A conta já é `Fraction`, o casamento de nome já é exato e
> já quebra listando candidatas. Este workstream ataca a limitação que aquela docstring **já
> declara sobre si mesma**, item 5: *"Ela não valida que a receita é real. O programa não
> conhece o crafting do jogo. Uma receita errada produz um número perfeitamente formatado e
> completamente falso. A única defesa que existe contra isso é que o usuário escreveu a
> receita."* Mapear por OCR é a resposta a essa frase.

## Por que workstream próprio

O mesmo critério que criou o `dashboard` como workstream próprio em 2026-09-01, e ele não
mudou: **GSD guarda progresso por `STATE.md`, e dois chats no mesmo arquivo colidem.** O
`mercado` está `Awaiting next milestone` e pode ter chat em cima dele. A dependência real aqui
é dupla e ambas são de leitura: `mercado_analise` (importado) e `.mercado/observacoes.csv`
(lido). Nenhum caminho de coleta existente é alterado.

## Fase 1 — a receita pela tela

- [ ] **RECE-01**: Uma **varredura única** da janela Special Craft grava um **catálogo de
      receitas em JSON**, escrito pelo programa. A janela não precisa ficar aberta depois: uma
      receita não muda de minuto a minuto como um preço, e pôr essa região no ciclo noturno
      custaria uma calibração a mais rodando a noite inteira para reler dado estático.
      **O `config.toml` do usuário nunca é reescrito** — critério já estabelecido duas vezes
      nesta árvore (`cambio.json`, ITEM-03): **quem escreve JSON é o programa, quem escreve
      TOML é o humano**, porque TOML tem comentário e é lá que se anota de onde o número veio.
      Os blocos `[[receita]]` escritos à mão continuam valendo e convivendo com o catálogo.

- [ ] **RECE-02**: O catálogo guarda o que a tela **mostra**, e nada além: o produto de cada
      resultado possível, a **probabilidade** e a **quantidade** de cada um, os ingredientes com
      suas quantidades, e as taxas em moeda. **Os números entre parênteses são o inventário do
      personagem e NÃO entram** — na captura de 2026-09-04, `Pedra da Rota x1 (110)` e `L-Coin
      x40 (30)`, onde `x1`/`x40` é a receita e `(110)`/`(30)` é a posse, com o segundo em
      vermelho por faltar. Gravar posse dentro de uma receita coloca o estado de um personagem
      num fato do jogo, e o catálogo passa a mentir no dia seguinte.

- [ ] **RECE-03**: A **mesma receita tem duas variantes de pagamento** — a tela tem um par de
      botões `Adena` | `XM`, e cada um mostra a sua taxa. As duas são lidas e gravadas como
      variantes do **mesmo produto**, não como receitas diferentes: é exatamente a comparação
      que o usuário pediu ("poderá ser craftado com adena ou por XM"), e separá-las em duas
      entradas faria a tela perder o vínculo que responde a pergunta.

- [ ] **RECE-04**: **Falha fechada, com o nome do que não foi lido.** Leitura incompleta —
      probabilidades que não fecham, quantidade ilegível, ingrediente sem nome — **não vira
      receita**; ela é recusada nomeando o campo, pelo precedente da `ReceitaInvalida`. Uma
      receita parcial produz um custo perfeitamente formatado e falso, que é o pior resultado
      possível deste workstream.

- [ ] **RECE-05**: As probabilidades são **o que o jogo afirma na tela**, e a tela diz isso.
      O programa lê `30% / 50% / 20%`; ele **não mediu** essas frequências e não tem como. É o
      mesmo tratamento do câmbio informado e do preço de NPC: número que o programa não mediu
      aparece atribuído à sua fonte, nunca como fato do programa.

- [ ] **RECE-06**: A varredura é **passiva como todo o resto**: captura de tela e OCR, sem
      injetar, sem ler memória, sem enviar input. **Nenhum clique no `Create`, nenhuma
      navegação automática pelas abas.** Quem troca de aba e rola a lista é o usuário; o
      scanner lê o que estiver na tela. FIRE-01 continua estruturalmente valendo.

## Fase 2 — o custo esperado, com a probabilidade dentro

- [ ] **CUST-01**: Para cada resultado possível, o programa responde **quanto custa produzir
      uma unidade dele**: o custo de uma tentativa **dividido pela probabilidade daquele
      resultado**. Se o Lv5 sai em 20% das tentativas, um Lv5 custa **cinco tentativas em
      média**. Esse é o número comparável com o preço de mercado do Lv5 — comparar o preço do
      Lv5 com o custo de *uma* tentativa é a conta errada, e é a que qualquer um faz de cabeça.
      Decisão do usuário, 2026-09-04.

      **O que essa fórmula assume, escrito porque ela parece mais sólida do que é:** que as
      tentativas são independentes e repetíveis, e que `1/p` é a **média** de tentativas, não o
      que vai acontecer com você. Metade das pessoas gasta mais que a média.

- [ ] **CUST-02**: O custo sai em **moedas separadas, sem inventar câmbio para o que ninguém
      mediu**. `Adena` casa com a série `adena#` e vira XM e R$ pelo câmbio que o dashboard já
      faz; **`L-Coin` não tem série no World Exchange** e por isso fica **fora do total
      convertido, dito em voz alta**, ao lado dele. Decisão do usuário, 2026-09-04, contra as
      duas alternativas: inventar um valor para a L-Coin produziria um total único e falso, e
      manter a regra atual do `margem_de_craft` (ingrediente sem série derruba a margem inteira)
      faria a receita da captura **nunca aparecer**.

      Isso é uma **divergência declarada do ANAL-04** e ela fica escrita no fonte, ao lado do
      código: lá, componente sem série mata a margem, porque lá todo componente é mercadoria.
      Aqui existe moeda que não é mercadoria, e matar a receita por causa dela seria cegueira.

- [ ] **CUST-03**: A comparação final é entre **três rotas**, não duas: craftar pagando a taxa
      em adena, craftar pagando a taxa em XM, e **comprar o item pronto no mercado**. A terceira
      é a que o `mercado_analise` já sabe responder e é a razão de o workstream existir. Toda
      comparação é sobre o **unitário em `Fraction`**, arredondando só no formatador — a mesma
      disciplina do CALC-01, pelo mesmo motivo: um veredito que vira de lado por meio centavo.

- [ ] **CUST-04**: **Os subprodutos não são descontados no v1, e a tela diz isso.** Quem crafta
      atrás de um Lv5 recebe Lv3 e Lv4 no caminho, e eles têm preço de mercado. Ignorá-los faz o
      custo do Lv5 sair **pessimista** — não é um erro de arredondamento, é uma direção. A conta
      líquida ("custo do Lv5 menos o que sai junto") é fase própria, porque depende de o mercado
      ter série para os três graus e de o usuário querer vender os subprodutos. O que o v1 não
      faz é omitir que o número é bruto.

- [ ] **CUST-05**: Abaixo do piso de evidência (`N_MINIMO_*` do `mercado_analise`) ou sem
      receita mapeada, a tela **diz que ainda não dá para responder**, com a frase de falta vinda
      do Python — nunca um custo chutado. Mesma regra do CALC-04, e ela pesa mais aqui: um custo
      de craft errado se descobre depois de gastar a adena.

## Fase 3 — a aba de Receitas

- [ ] **ABA-01**: A página do dashboard ganha uma **aba de Receitas**, ao lado do que já existe.
      Uma linha por receita mapeada, cada uma mostrando os resultados possíveis com seu custo
      esperado, as três rotas, e a vencedora marcada. **As rotas perdedoras continuam visíveis** —
      esconder a perdedora impede conferir a conta, e esta conta é sobre dinheiro real (precedente
      da Fase 2 do `dashboard`).

- [ ] **ABA-02**: Cada número carrega **de onde veio**: preço de mercado traz `n` e recência;
      probabilidade traz "o jogo diz"; câmbio XM→BRL traz "informado por você, em tal data";
      custo esperado traz "derivado". Nenhum número aparece sem procedência — é a regra que já
      vale na tela inteira.

- [ ] **ABA-03**: Receita mapeada cujo produto **nunca apareceu no mercado** aparece assim
      mesmo, dizendo que falta o lado do mercado. Sumir seria indistinguível de "esqueci de
      mapear" — precedente literal do item configurado sem série, na Fase 2 do `dashboard`.

- [ ] **ABA-04**: O dashboard continua **somente-leitura** sobre os dados (DASH-01): ele lê o
      catálogo de receitas, não o escreve. Quem escreve o catálogo é a varredura da Fase 1, em
      processo separado. Derrubar o dashboard não perde receita mapeada.

## Riscos medidos e por medir

- **⚠️ Idioma misturado, por medir.** Na captura, `Pedra da Rota` está em português enquanto o
  World Exchange grava `Common Fafurion Doll` em inglês. O casamento de nome é **exato de
  propósito** — é ele que impede `B-grade Gemstone` de virar `C-grade Gemstone` (similaridade
  0,9375, medida no `mercado`). Se as duas telas nomearem o mesmo item em idiomas diferentes, o
  casamento quebra corretamente e **parece defeito**. Isso se resolve por **medição** assim que
  houver leitura das duas telas, não por decisão antecipada; o plano da Fase 2 não pode assumir
  que casa.
- **A tela de craft é uma superfície de OCR nova**, com lista rolável à esquerda, números com
  vírgula de milhar, percentuais, e **cor carregando significado** (vermelho = falta no
  inventário). Nada disso está calibrado hoje.

## Restrições herdadas — valem no workstream inteiro

- **FIRE-01**: nenhuma biblioteca de síntese de input entra na árvore. O `Create` nunca é
  clicado pelo programa.
- **Detecção passiva**: captura de tela e OCR apenas. Nunca injetar, ler memória ou enviar input.
- **Nunca acoplar ao detector de morte** (`rastreador.py`, `visao.py`).
- **Zero-install**: dependência nova é decisão de pesquisa com justificativa.
- **Falha fechada**: dado incompleto é descartado, nunca interpretado.
- **Nada de constante mágica**, e **um número que caiu precisa dizer que caiu**.

## Rastreabilidade

| ID | Fase | Estado |
|---|---|---|
| RECE-01 | Phase 1 | Pending |
| RECE-02 | Phase 1 | Pending |
| RECE-03 | Phase 1 | Pending |
| RECE-04 | Phase 1 | Pending |
| RECE-05 | Phase 1 | Pending |
| RECE-06 | Phase 1 | Pending |
| CUST-01 | Phase 2 | Pending |
| CUST-02 | Phase 2 | Pending |
| CUST-03 | Phase 2 | Pending |
| CUST-04 | Phase 2 | Pending |
| CUST-05 | Phase 2 | Pending |
| ABA-01 | Phase 3 | Pending |
| ABA-02 | Phase 3 | Pending |
| ABA-03 | Phase 3 | Pending |
| ABA-04 | Phase 3 | Pending |
