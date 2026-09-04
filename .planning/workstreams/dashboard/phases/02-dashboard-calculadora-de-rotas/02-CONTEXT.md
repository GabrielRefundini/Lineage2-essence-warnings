# Phase 2: A calculadora de rotas de compra - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning
**Mode:** Smart discuss (autônomo, 3 áreas, todas aceitas como propostas)

<domain>
## Phase Boundary

Para um item, o dashboard responde **"sai mais barato comprando no mercado com XM, ou comprando
do NPC com adena?"** — com Gemstone C e Gemstone B como as duas primeiras instâncias.

**Dentro:** a conta das duas rotas, a configuração do preço de NPC, o veredito com sua faixa de
empate, a quarta região da página, e os testes que provam tudo sem navegador.

**Fora:** ler o preço do NPC por captura de tela (não existe segunda fonte — decisão do usuário);
qualquer alteração no caminho da coleta; a aba de negociação virar tela própria.
</domain>

<decisions>
## Implementation Decisions

### A conta e o veredito

- **O veredito usa o MENOR PEDIDO VISÍVEL**, não a mediana: é o que o usuário pagaria se
  comprasse agora. A mediana aparece ao lado como contexto — ela responde "o mercado está caro?",
  que é outra pergunta.
- **Existe faixa de empate**, declarada em percentual. Abaixo dela a tela diz *empatado* em vez de
  eleger um vencedor por 0,3%. O número é **ESCOLHA declarada em constante nomeada no fonte**, não
  medição — mesmo tratamento que os pisos de evidência receberam na Fase 4 do `mercado`.
- **A diferença sai em XM, em % e em R$.** O XM é o denominador que sempre existe; o % é o que se
  lê rápido; o R$ desaparece junto com o câmbio, como todo valor derivado dele.
- **A comparação é sempre sobre o unitário derivado em `Fraction`**, com o custo do pacote do NPC
  mostrado ao lado como ele realmente vende. Comparar pacote com pacote quebra no dia em que o
  NPC e o mercado usarem tamanhos diferentes.

### A configuração dos itens

- **O preço do NPC mora no `config.toml`**, em blocos `[[dashboard.item]]`. O critério que separa
  este arquivo do `cambio.json` não é gosto: **o `cambio.json` é escrito pelo navegador**, e por
  isso é JSON de máquina; **o preço de NPC é escrito à mão, uma vez**, e TOML tem comentário — que
  é onde o usuário anota de qual NPC aquele preço veio.
- **Uma entrada tem três campos:** o nome exato como aparece no jogo, o preço do NPC em adena, e a
  quantidade que o NPC vende por vez.
- **Entrada torta DERRUBA O ARRANQUE**, nomeando o item e o campo. É o precedente da
  `ReceitaInvalida` da Fase 4 do `mercado`: a watchlist podia degradar porque só promovia séries no
  console, mas **uma conta torta que degradasse para "sem resposta" sairia calada** — e esta conta
  é sobre dinheiro real.
- **Item configurado que nunca apareceu no CSV aparece na tela dizendo isso.** Sumir seria
  indistinguível de "esqueci de configurar".

### A tela

- **Quarta região**, abaixo da procedência, com a mesma receita de painel entalhado do tema. A
  pergunta do topo continua sendo "quanto vale 1 milhão de adena"; a calculadora é a pergunta
  seguinte, não a que compete com ela.
- **Uma linha por item**, cada uma com seu veredito. Sem seletor: dois cliques para a mesma
  resposta é pior que duas linhas.
- **As duas rotas aparecem SEMPRE, com a vencedora marcada.** Esconder a perdedora impede conferir
  a conta, e esta conta é sobre dinheiro real.
- **Atualiza no mesmo polling de ~2s** que já existe. O veredito muda sozinho quando a taxa da
  Adena mexe — que é justamente o motivo de a calculadora viver num painel ao vivo e não num papel.

### Claude's Discretion

- O nome dos módulos, a forma interna do bloco no payload, o valor exato da margem de empate (com
  a razão escrita), e como a quarta região se encaixa na precedência de estados que já existe.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **A taxa Adena→XM ao vivo** já é produzida pela Fase 1 (`dashboard_dados`), derivada da série
  `adena#` com `Fraction` exata.
- **`mercado_analise`** — `menor_pedido_visivel`, `mediana_dos_unitarios`, `unitario`,
  `recencia_do_preco`, `Evidencia` e os pisos `N_MINIMO_*`. A calculadora consome tudo isso; não
  reimplementa nada.
- **`mercado_analise.nome_normalizado` + o casamento EXATO** com quebra por ambiguidade listando
  candidatas. É o que impede a Gemstone B de virar Gemstone C, e a razão de não inventar um segundo
  casamento aqui está medida na Fase 4 do `mercado`: o corte de similaridade 0,8947 junta
  `+3 Dragon Belt` com `+4 Dragon Belt` (0,9286).
- **`dashboard_cambio`** — o molde de "valor informado pelo usuário, com carimbo e portão de duas
  camadas". O preço de NPC segue a mesma disciplina de declaração, com a fonte diferente.
- **A quarta região** herda a receita de painel, os tokens e a precedência de estados do
  `01-UI-SPEC.md`.

### Established Patterns

- `Fraction` em toda comparação de preço; arredondamento só no formatador.
- Todo número exibido carrega `n` e recência; o derivado diz que é derivado.
- Constante de julgamento é nomeada com a razão escrita, e declarada ESCOLHA quando não é medição.
- Refutação mora no fonte, ao lado do código que a substituiu.
- Config lido por `tomllib` (read-only) — o dashboard nunca escreve no `config.toml`.

### Integration Points

- **Entrada:** `.mercado/observacoes.csv` (somente leitura), `.mercado/cambio.json` (para o R$),
  e agora `config.toml` (para o preço de NPC).
- **Saída:** um bloco novo no payload de `/dados`, e a quarta região no `index.html`.
- **Nada** do caminho do `--mercado` é tocado.
</code_context>

<specifics>
## Specific Ideas

- O pedido original do usuário: *"uma calculadora para saber se compensa comprar gemstone grade
  C / B por adena ou por XM"*.
- A fonte do preço em adena é **NPC com preço fixo** (decisão do usuário, 2026-09-02) — não há
  segunda fonte em tela, então o número é configuração.
- **O veredito não depende do câmbio XM→BRL**, porque ele cancela na comparação. Está escrito por
  extenso no ROADMAP da fase; é o achado que faz a calculadora continuar respondendo no dia em que
  o câmbio estiver vazio ou velho.
</specifics>

<deferred>
## Deferred Ideas

- **Ler o preço do NPC por captura de tela** — descartado nesta fase por não existir fonte; se um
  dia o NPC virar tela lida, é fase própria com calibração própria.
- **Comparar mais de duas rotas** (ex.: craftar em vez de comprar) — a estrutura genérica não
  impede, mas o v1 compara duas.
- **Histórico do veredito ao longo do tempo** ("desde quando compensa comprar por adena") — cabe no
  componente de série que já existe, e é fase própria.
</deferred>
