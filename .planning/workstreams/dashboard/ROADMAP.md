# Roadmap: Dashboard do câmbio (workstream `dashboard`)

**Workstream:** dashboard (`.planning/workstreams/dashboard/`)
**Milestone:** v1-dashboard — o câmbio Adena → XM → BRL, ao vivo, no navegador local
**Created:** 2026-09-01
**Granularity:** coarse (1 fase)
**Ponto de partida:** o `--mercado` já lê a aba Adena e grava `.mercado/observacoes.csv`
(v2-mercado, Fase 5, ADEN-01..04 completos). O console já calcula menor pedido visível,
mediana `median_low` e tendência. **Nada disso se reconstrói** — o dashboard é uma
superfície nova sobre dado que já existe.

## Por que workstream próprio, e não uma fase do `mercado`

Duas razões, e a segunda é a que decide.

1. **Paralelismo real.** O usuário tem chats rodando ao mesmo tempo no `mercado`. GSD guarda
   progresso por workstream (`STATE.md`), e dois agentes avançando o mesmo arquivo colidem —
   dor já paga nesta árvore (o `tiat` roda isolado por isso). Como workstream próprio, esta
   fase planeja e executa em paralelo sem tocar no estado do mercado.

2. **A dependência é um arquivo, não código.** O contrato entre os dois é
   `.mercado/observacoes.csv` — seis colunas, separador `;`, terminador de linha. O dashboard
   nunca importa o laço de captura, nunca abre o `calibration.json`, nunca vê um pixel. Um
   acoplamento de código exigiria co-planejamento; um acoplamento de arquivo não.

---

## Phase 1: Dashboard do cambio ao vivo

**Goal**: uma página no navegador local responde "quanto vale 1 milhão de adena agora, em XM e em R$" e mostra a história dessa taxa com zoom — lendo o CSV que o `--mercado` já grava, sem tocar na coleta.

**Depends on**: Nothing — dentro deste workstream esta é a primeira fase. A dependência externa (a taxa da Adena gravada no CSV) já está pronta e verificada no workstream `mercado`, e não há nada a construir do lado de lá.

**Requirements**: DASH-01 a DASH-06

### O escopo, do jeito que o usuário decidiu (2026-09-01)

- **Só Adena no v1.** A aba de negociação fica de fora da tela; o *componente* que desenha a
  série nasce genérico (DASH-05), mas a única instância ligada é a taxa da Adena.
- **Tempo real, para decidir agora.** Não é ferramenta de análise pós-sessão.
- **Navegador, mesmo PC.** Sem rede, sem celular, sem autenticação — isso é v2 e nem foi
  pedido.
- **A conta que importa é Adena → XM → BRL.** O jogo só dá metade (Adena → XM). A outra
  metade é digitada por você (hoje `1 XM = R$ 0,50`) e por isso é sempre **declarada como
  informada**, nunca apresentada como medida.

### Success Criteria (o que tem que ser VERDADE)

1. Com o `--mercado` coletando, o dashboard aberto mostra o valor de agora e **uma página
   nova lida pelo scanner aparece na tela sem recarregar à mão**. — DASH-01, DASH-04
2. Matar o dashboard **não interrompe a coleta**, e matar o scanner deixa o dashboard vivo
   mostrando o último dado **com a recência na cara** — ele não afirma "agora" sobre um
   número de três horas atrás. — DASH-06, DASH-04
3. Digitar `0,50` no campo de câmbio faz os valores em R$ aparecerem; fechar o navegador e
   reabrir **mantém o valor**; a tela diz que ele foi informado por você e quando. — DASH-02
4. **Sem taxa informada**, a página mostra XM normalmente e diz que o R$ está indisponível.
   Nenhum valor padrão é chutado — um câmbio inventado vira decisão de dinheiro real errada.
   — DASH-02
5. O gráfico mostra **duas linhas** (menor pedido visível e mediana `median_low`), com zoom de
   horas do dia até dias atrás, e os números batem com os que o console `--mercado` imprime
   para o mesmo instante — mesma fonte, mesma conta, sem um segundo parser. — DASH-03
6. O CSV é aberto **somente para leitura**: rodar o dashboard por uma sessão inteira não muda
   tamanho, conteúdo nem mtime do arquivo. Provado por medição, não por intenção. — DASH-01
7. Com o scanner **apendando durante a leitura**, o dashboard não exibe linha parcial e não
   some com a série: degrada para "a última linha completa". Provado cortando o arquivo no
   meio de uma linha. — DASH-01
8. O componente de série é instanciável para uma segunda série **sem código de gráfico novo** —
   provado instanciando uma série de negociação num teste, mesmo com a tela do v1 só mostrando
   Adena. — DASH-05
9. `dashboard.bat` sobe a interface em dois cliques, e o caminho do `--mercado` fica
   **byte-idêntico** — nenhuma linha do modo mercado muda por causa desta fase. — DASH-06

### Riscos e decisões que o planejamento tem que encarar

- **O contrato do terminador não serve como está.** A Fase 3 do mercado decidiu, com razão,
  que arquivo que não termina em quebra de linha é contrato quebrado → *a feature desliga
  alto e nada é lido*. Para um leitor **ao vivo**, essa regra é a errada: o scanner apenda
  1 Hz, e o dashboard cairia em cegueira toda vez que pegasse o arquivo no meio de uma
  escrita. A degradação correta aqui é **"leio até a última linha completa"**. Isso é uma
  divergência deliberada de uma regra existente e precisa estar escrita no fonte, do jeito
  que a casa escreve refutação — não pode ser copiada por descuido nem revertida por
  simetria.

- **Onde mora a taxa XM→BRL.** Não é calibração de pixel (fora do `calibration.json`, que o
  mercado lê e nunca escreve) e não pode ser `config.toml` (o `tomllib` da stdlib é
  **read-only**, e quem escreve é o navegador). Pela mesma lógica que separou os dois
  arquivos no projeto, o candidato natural é um JSON pequeno escrito pelo dashboard. A
  decisão é do plano; o que não é negociável é que o mercado **não passe a depender dele**.

- **A stack do gráfico sob a doutrina de zero-install.** O `rich` já foi recusado no console
  de mercado por essa doutrina, e o FIRE-01 continua valendo. As rotas plausíveis: `http.server`
  da stdlib servindo uma página com JS de gráfico **vendorizado na árvore** (zero dependência
  Python, zero rede), CDN (uma dependência de internet a cada abertura), ou render no servidor.
  **Isto é pesquisa da fase, não decisão deste roadmap.** O que já está decidido é que existe
  um servidor local: página `file://` não consegue ler o CSV por `fetch`, e essa rota foi
  recusada na exploração.

- **O ponto do gráfico quando o zoom é largo.** Cada tick produz várias ofertas; menor e
  mediana já são por página lida. Ao mostrar dias, vários ticks caem no mesmo pixel e alguém
  tem que decidir o que aquele ponto significa. A disciplina D-02 vale aqui inteira: **um
  número exibido tem de ter existido** — `median_low` de novo, nunca uma média que inventa
  meio centavo. Escolha declarada no fonte, como os pisos de evidência da Fase 4.

- **`n` e recência acompanham todo número**, como já é regra no console. Um valor de R$ com
  `n=1` de duas horas atrás e um com `n=30` de agora **não podem sair iguais na tela**.

**Plans:** 8 plans, em 5 ondas de execucao

Plans:
- [ ] 01-01-PLAN.md — O corte da RAIZ e o tracer de ponta a ponta: do byte do CSV ao numero na tela (onda 1)
- [ ] 01-02-PLAN.md — A leitura ao vivo endurecida, a agregacao por instante e o payload com precedencia de estados (onda 2)
- [ ] 01-03-PLAN.md — O cambio XM para BRL: portao de duas camadas e persistencia carimbada e atomica (onda 2)
- [ ] 01-04-PLAN.md — A biblioteca vendorizada: VEND-1 proveniencia, VEND-2 revisao de fonte, VEND-3 o teste que quebra (onda 2)
- [ ] 01-05-PLAN.md — O servidor completo: bind exclusivo, listagem desligada, portao de origem no POST, cache e as provas sem navegador (onda 3)
- [ ] 01-06-PLAN.md — A pagina: as tres regioes e o tema de Lineage 2, com contraste recalculado por teste (onda 3)
- [ ] 01-07-PLAN.md — O dashboard.js: polling, estados, o componente de serie generico e o zoom escrito por nos (onda 4)
- [ ] 01-08-PLAN.md — O lancador dashboard.bat e a prova sem navegador da generalidade da serie (onda 5)

**Nota do planejamento (2026-09-01):** a rota (a) recomendada pela pesquisa para a leitura ao
vivo tocaria `mercado_registro.py`, o que CTX-2 nao autoriza — ela foi trocada por um adaptador
com forma de `Path` que mantem um parser so e zero arquivos do `mercado` alterados. E a segunda
aresta do grafo de import **nao** e cortada: `mercado_console` arrasta OpenCV e numpy pela cadeia
do console, medido em 350 modulos, o que invalida em parte a justificativa escrita no DASH-06. A
promessa que sobrevive — nenhuma mudanca de comportamento no caminho da coleta — segue de pe, e
a refutacao fica escrita no fonte.

**Nota de nomenclatura:** os slugs de diretório levam o prefixo `dashboard-`
(ex.: `phases/01-dashboard-cambio-ao-vivo/`), pelo mesmo motivo do `mercado` e do `tiat` —
escopos de commit não podem colidir entre workstreams.

---

## Phase 2: A calculadora de rotas de compra

**Goal**: para um item, o dashboard responde **"sai mais barato comprando no mercado com XM, ou comprando do NPC com adena?"** — com a Gemstone C e a B como as duas primeiras instâncias, e a conta valendo em R$ quando você tiver informado o câmbio.

**Depends on**: Fase 1 (a taxa Adena→XM ao vivo, a leitura do CSV, o servidor e a página já existem; esta fase compõe o que está lá, não constrói coletor novo).

**Requirements**: CALC-01 a CALC-05

### O que o usuário decidiu (2026-09-02)

- **O preço em adena vem de NPC e é fixo** — não há segunda fonte para o scanner ler. Ele vira configuração escrita uma vez, com o mesmo tratamento do câmbio XM→BRL: declarado como informado por você e quando, nunca apresentado como medido.
- **A calculadora nasce genérica**, com Gemstone C e B como primeira instância — mesma disciplina do DASH-05. "Este item, por qual rota" é a conta; os dois itens são linhas de configuração, não `if` no código.

### A descoberta que muda o desenho: o veredito não depende do câmbio

As duas rotas terminam multiplicadas pelo **mesmo** `reais_por_xm`, então ele **cancela na comparação**:

    rota NPC     = preco_npc_adena x taxa_xm_por_adena x reais_por_xm
    rota mercado = preco_mercado_xm                    x reais_por_xm

Logo **"qual é mais barata" se responde sem câmbio nenhum informado** — basta XM como denominador comum. O `reais_por_xm` só é necessário para dizer **quanto** em dinheiro real, não **qual**. Consequência de produto, e não detalhe de implementação: no dia em que o câmbio estiver vazio ou velho, o veredito continua na tela e só o valor em R$ some — exatamente a mesma regra ortogonal que a Fase 1 já aplica ao cartão de R$.

### Success Criteria (o que tem que ser VERDADE)

1. Com o preço de NPC configurado para Gemstone C e a taxa da Adena lida do CSV, a tela diz qual rota é mais barata **e por quanto**, em XM. — CALC-01, CALC-02
2. **Sem nenhum câmbio XM→BRL informado**, o veredito continua aparecendo; só o "quanto em R$" some. Provado por teste, não por intenção. — CALC-03
3. Quando o preço de mercado do item está **abaixo do piso de evidência** (`N_MINIMO_*`, que já existem), a tela diz que ainda não dá para responder, com a frase de falta vinda do Python — **nunca um veredito chutado sobre `n=1`**. — CALC-04
4. Acrescentar um terceiro item (ex.: Soulstone) é **uma entrada de configuração**, sem código novo de cálculo nem de tela — provado instanciando um terceiro no teste. — CALC-05
5. O preço de NPC aparece na tela declarado como **informado por você**, com **de onde ele veio e quando o programa o leu**. — CALC-02
   **Emendado em 2026-09-03, no planejamento.** A redação anterior era *"informado por você e quando, do mesmo jeito que o câmbio"*, e ela não é entregável: o `cambio.json` tem data porque **o programa o escreve**, e o `config.toml` não. Fabricar o "quando" a partir da data de modificação do arquivo diria algo falso sobre o preço toda vez que outra seção do mesmo arquivo fosse editada. O que a tela mostra no lugar é o instante da **leitura** no arranque — um fato do programa, que ainda por cima responde "o dashboard que está rodando já conhece a minha correção?", pergunta que esta fase cria ao ler a configuração uma vez só. A razão inteira, com as três candidatas e o destino de cada uma, está no CALC-02 do `REQUIREMENTS.md`.
6. A comparação é em `Fraction`, e o arredondamento acontece só na formatação — um veredito que vira do lado errado por meio centavo é o defeito que essa disciplina existe para impedir. — CALC-01

### Riscos e decisões que o planejamento tem que encarar

- **A unidade de venda pode não bater.** O NPC pode vender em pacote e o mercado em unidade (ou vice-versa). A conta tem de ser sobre o **unitário derivado em `Fraction`**, como já é a regra do `mercado_analise`, e o plano precisa dizer de onde sai a quantidade de cada rota.
- **O item precisa ser identificado no CSV**, e o nome vem de OCR, que oscila. O casamento por nome exato já foi resolvido no `mercado_analise` (`nome_normalizado`, casamento exato, ambiguidade QUEBRA listando as candidatas) — reusar aquilo, e não inventar um segundo casamento, é o que impede a Gemstone B de virar Gemstone C.
- **O veredito é uma afirmação sobre dinheiro.** Ele carrega `n` e recência como todo número da casa, e quando as duas rotas empatam dentro da margem do dado disponível, dizer "empatado" é resposta melhor que escolher um lado.

**Plans:** 4 plans, em 4 ondas de execucao

Plans:
- [ ] 02-01-PLAN.md — O tracer: do bloco `[[dashboard.item]]` ao veredito na quarta regiao (onda 1)
- [ ] 02-02-PLAN.md — O piso do veredito, a diferenca em XM/%/R$, e o R$ que some sozinho (onda 2)
- [ ] 02-03-PLAN.md — A quarta regiao completa: os seis estados, a perdedora que nao some, a procedencia do preco do NPC (onda 3)
- [ ] 02-04-PLAN.md — A prova de que um terceiro item e so uma entrada de configuracao, com controle em cada elo (onda 4)

**Nota do planejamento (2026-09-03):** as quatro ondas sao **sequenciais de proposito**, e nao um
lapso de paralelismo. Esta fase e composicao: os quatro planos disputam os mesmos tres arquivos de
producao (`dashboard_rotas.py`, `dashboard_dados.py` e os tres arquivos web), e dois planos na
mesma onda tocando o mesmo arquivo e a colisao que o proprio ROADMAP deste workstream existe para
evitar. A pesquisa foi **deliberadamente pulada**: nenhuma biblioteca nova, nenhum protocolo novo,
nenhuma leitura de tela nova — a fase compoe modulos que a Fase 1 ja pesquisou e entregou.

**Duas decisoes que o planejamento teve de tomar, e que o ROADMAP nao antecipava:**

1. **O piso do veredito nao pode ser `N_MINIMO_PARA_MENOR`.** Ele vale **1**, e reusa-lo
   literalmente produziria exatamente o veredito sobre `n=1` que o CALC-04 chama de pior que
   nenhum veredito. O piso do veredito fica **ligado** a `N_MINIMO_PARA_MEDIANA` — um piso que ja
   existe —, com a razao escrita no fonte: o piso do menor guarda um numero OBSERVADO, e este
   guarda uma ELEICAO de rota com dinheiro real.
2. **A procedencia do preco do NPC nao carrega carimbo, e isso e honestidade e nao omissao.** O
   CALC-02 pede "informado por voce **e quando**", pelo espelho do cambio — mas o `cambio.json`
   guarda historico com data e o `config.toml` nao e escrito pelo programa. A tela diz de ONDE o
   numero veio, que e o que existe, e **nao inventa um quando**. A divergencia fica escrita na
   marcacao.

**Medido em 2026-09-03, e o que ele muda:** o `.mercado/observacoes.csv` real tem duas series —
`adena#` (n=50) e `common-fafurion-doll#` (n=8) — e **nenhuma Gemstone**. Com Gemstone C
configurada, a PRIMEIRA tela que o usuario vai ver e a linha de item nunca visto, exatamente como
o estado vazio foi a primeira tela da Fase 1. E na taxa de hoje, um preco de NPC abaixo de ~555,6
adena por unidade faz o unitario arredondar para duas casas zeradas — a armadilha do `0,00` desta
fase e real e alcancavel, nao teorica.

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Dashboard do cambio ao vivo | 8/8 | Executed — verificação humana pendente | - |
| 2. A calculadora de rotas de compra | 0/4 | Planned | - |

## Coverage

| Requirement | Phase |
|-------------|-------|
| DASH-01 | Phase 1 |
| DASH-02 | Phase 1 |
| DASH-03 | Phase 1 |
| DASH-04 | Phase 1 |
| DASH-05 | Phase 1 |
| DASH-06 | Phase 1 |
| CALC-01 | Phase 2 — planos 02-01, 02-02 |
| CALC-02 | Phase 2 — planos 02-01, 02-03 |
| CALC-03 | Phase 2 — planos 02-02, 02-03 |
| CALC-04 | Phase 2 — planos 02-02, 02-03 |
| CALC-05 | Phase 2 — planos 02-02, 02-04 |

**11 de 11 requisitos mapeados. Nenhum órfão.**

## Restrições herdadas — valem no workstream inteiro

- **FIRE-01 continua valendo**: nenhuma biblioteca de síntese de input entra na árvore.
- **O dashboard nunca escreve no `.mercado/observacoes.csv`** e nunca lê o `calibration.json`.
- **Nunca acoplar ao detector de morte** (`rastreador.py`, `visao.py`) — a manobra do
  incidente 27x.
- **Falha fechada**: dado ilegível ou incompleto é descartado, nunca interpretado. Câmbio
  ausente é dito, nunca chutado.
- **Um número que caiu precisa dizer que caiu** — refutações ficam no fonte.

---
*Roadmap criado: 2026-09-01, a partir de `/gsd-explore`*
