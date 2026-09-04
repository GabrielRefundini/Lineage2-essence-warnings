# Roadmap: Receitas de craft (workstream `receitas`)

**Workstream:** receitas (`.planning/workstreams/receitas/`)
**Milestone:** v1-receitas — a receita lida da tela, e o custo real de craftar em adena, XM e R$
**Created:** 2026-09-04
**Granularity:** média (3 fases)
**Ponto de partida:** o `mercado` já entregou o **ANAL-04** — `margem_de_craft`,
`config.Receita`, `ComponenteDaReceita`, `ler_receitas`, `ReceitaInvalida` — com a conta em
`Fraction` e o casamento de nome exato que quebra listando candidatas. **A conta não se
reimplementa.** O `dashboard` já entregou a página, o câmbio informado e a calculadora de rotas.

## O que o usuário pediu, e o que a captura revelou

Pedido, 2026-09-04: *"mapear as receitas por OCR... quantos XMs e Reais (BRL) está custando
realmente fazer isso... uma aba de Receitas... esse mesmo recurso poderá ser craftado com adena
ou por XM"*.

A captura da janela **Special Craft** mostra quatro coisas que o modelo atual não comporta, e
elas são a razão de isto ser um milestone e não um `/gsd-quick`:

1. **O craft não tem um resultado, tem uma distribuição** — `Lv3 30%`, `Lv4 50%`, `Lv5 20%`,
   `Quantity 1` em cada. O campo de hoje é `Receita.rende: int`. Isso **não** é a "chance de
   falha" que a docstring do `margem_de_craft` já cita como limitação: não falha, sai outro item.
2. **A taxa mistura mercadoria e moeda** — `Pedra da Rota x1`, `L-Coin x40`, `Adena x200.000`.
   A adena casa com a série `adena#` e cai no câmbio que o dashboard já faz; a **L-Coin não tem
   série nenhuma**, e a regra atual (componente sem série derruba a margem inteira) faria esta
   receita nunca aparecer.
3. **Os parênteses são inventário, não receita** — `(110)`, `(30)`, o segundo em vermelho por
   faltar. É estado do personagem, e não pode entrar num catálogo de fatos do jogo.
4. **Um par de botões `Adena` | `XM`** dá duas variantes de pagamento para o mesmo produto —
   que é literalmente a comparação pedida.

---

## Phase 1: A receita pela tela

**Goal**: uma varredura da janela Special Craft grava um catálogo de receitas em JSON — cada resultado com sua probabilidade e quantidade, cada ingrediente com a sua, e as taxas em adena e em XM — recusando nomeadamente toda leitura incompleta, sem tocar no config.toml do usuário e sem clicar em nada.

**Depends on**: Nothing — é a primeira fase deste workstream. O que ela consome do `mercado` (o pipeline de captura e OCR) já está pronto e verificado, e não há nada a construir do lado de lá.

**Requirements**: RECE-01 a RECE-06

### Success Criteria (o que tem que ser VERDADE)

1. Com a Special Craft aberta na receita da captura, uma varredura grava um catálogo JSON com
   **três resultados** (`30/50/20`, `Quantity 1` cada), **dois ingredientes** (`x1`, `x40`) e a
   **taxa em adena** (`200.000`) — e **nenhum** dos números entre parênteses. — RECE-01, RECE-02
2. Trocar o botão para `XM` e varrer de novo acrescenta a **variante de pagamento ao mesmo
   produto**, não uma segunda receita. — RECE-03
3. Ocultar ou borrar um campo faz a receita ser **recusada nomeando o campo**, e o catálogo fica
   sem ela em vez de ficar com ela pela metade. — RECE-04
4. O `config.toml` do usuário sai **byte-idêntico** da varredura, e um `[[receita]]` escrito à
   mão continua sendo lido normalmente. — RECE-01
5. A árvore de dependências continua **sem biblioteca de input**, e o código da varredura não
   tem caminho que envie clique, tecla ou navegação ao jogo. — RECE-06
6. As probabilidades aparecem no catálogo **atribuídas ao jogo**, e nada no código as apresenta
   como frequência medida. — RECE-05

---

## Phase 2: O custo esperado, com a probabilidade dentro

**Goal**: para cada resultado de cada receita mapeada, o programa responde quanto custa produzir uma unidade dele — o custo da tentativa dividido pela probabilidade daquele resultado — em adena, XM e R$, com a L-Coin declarada fora do total, e compara as três rotas contra o preço de mercado do item pronto.

**Depends on**: Phase 1 — sem catálogo não há o que calcular.

**Requirements**: CUST-01 a CUST-05

### Success Criteria (o que tem que ser VERDADE)

1. Para um resultado de 20%, o custo por unidade é **cinco vezes** o custo da tentativa, em
   `Fraction` exata, e um teste prova isso com números conhecidos. — CUST-01
2. A conta produz **três rotas** para o mesmo produto — craft pagando em adena, craft pagando em
   XM, comprar pronto — sobre o unitário, e diz qual é a mais barata e por quanto. — CUST-03
3. A **L-Coin fica fora do total convertido e é dita em voz alta**, e a receita **continua
   aparecendo** — o oposto do que o `margem_de_craft` faz hoje, com a divergência escrita no
   fonte ao lado do código. — CUST-02
4. Sem câmbio XM→BRL informado, o custo em XM **continua na tela** e só o R$ some — mesma regra
   ortogonal do CALC-03. — CUST-03
5. A saída **declara que o custo é bruto** e que os subprodutos não estão descontados, com a
   direção do viés nomeada (pessimista). — CUST-04
6. Abaixo do piso de evidência, sai a frase de falta vinda do Python, **nunca um custo**. — CUST-05
7. **A questão do idioma é medida, não assumida**: um teste confronta os nomes lidos da tela de
   craft com as chaves de série do CSV e **reporta o que casou e o que não casou**, em vez de o
   plano supor que casa.

---

## Phase 3: A aba de Receitas

**Goal**: a página do dashboard ganha uma aba de Receitas que mostra, por receita, os resultados com seu custo esperado e as três rotas com a vencedora marcada — cada número com a sua procedência, e sem o dashboard nunca escrever no catálogo.

**Depends on**: Phase 2 — a aba exibe o que a conta produz.

**Requirements**: ABA-01 a ABA-04

### Success Criteria (o que tem que ser VERDADE)

1. A aba lista as receitas mapeadas, com **as rotas perdedoras visíveis** ao lado da vencedora. — ABA-01
2. Todo número na aba carrega procedência: `n` e recência para preço de mercado, "o jogo diz"
   para probabilidade, "informado por você" para o câmbio, "derivado" para o custo. — ABA-02
3. Receita cujo produto **nunca apareceu no mercado** aparece dizendo isso, em vez de sumir. — ABA-03
4. O dashboard **não escreve** no catálogo, e derrubá-lo não perde receita mapeada. — ABA-04

---

## Fora de escopo neste milestone

- **Descontar os subprodutos** do custo do resultado desejado (a conta líquida). Depende de o
  mercado ter série para todos os graus — é fase própria, e CUST-04 obriga a tela a dizer que o
  número é bruto até lá.
- **Navegar as abas do craft automaticamente** (Weapon/Armor/Accessories/Misc/Upgrade/Event) —
  isso exigiria enviar input, e FIRE-01 fecha essa porta por construção.
- **Receita que consome item craftável** (recursão de custo). O v1 precifica ingrediente pelo
  mercado; se um ingrediente for ele próprio craftável, o v1 não desce um nível.
- **Histórico do custo ao longo do tempo.** Cabe no componente de série que a Fase 1 do
  `dashboard` já deixou genérico, e é fase própria.
