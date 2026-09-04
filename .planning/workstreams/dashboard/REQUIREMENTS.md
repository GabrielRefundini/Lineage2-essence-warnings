# Requisitos — v1-dashboard

**Workstream:** dashboard
**Milestone:** v1-dashboard — o câmbio Adena → XM → BRL, ao vivo, no navegador local
**Criado:** 2026-09-01, a partir de `/gsd-explore`

> A fonte de dados é o `.mercado/observacoes.csv`, gravado pelo `--mercado` do workstream
> `mercado` (v2-mercado, Fase 5, ADEN-01..04 completos). Este workstream **não** coleta nada.

## Fase 1 — o câmbio em BRL, ao vivo

- [ ] **DASH-01**: O dashboard é uma superfície **somente-leitura** sobre o
      `.mercado/observacoes.csv`. Ele nunca escreve nesse arquivo, e a coleta não depende dele
      estar de pé. Lendo enquanto o scanner apenda, ele **não exibe linha parcial e não perde
      a série**: degrada para a última linha completa. Essa é uma divergência declarada da
      regra do terminador da Fase 3 do mercado — lá o contrato quebrado desliga a feature
      alto, aqui isso viraria cegueira a cada escrita —, e a divergência fica escrita no fonte.

- [ ] **DASH-02**: A taxa **XM → BRL é entrada manual** do usuário (hoje `1 XM = R$ 0,50`),
      editável na própria página e **persistida entre sessões**. Todo valor em R$ é derivado
      dela e é declarado na tela como *informado por você, em tal data* — nunca apresentado
      como medido. Sem taxa informada, a página mostra XM normalmente e diz que o R$ está
      indisponível: **nenhum valor padrão é chutado**.

- [ ] **DASH-03**: A história da taxa aparece como **linha do tempo com zoom** — das horas do
      dia até dias atrás — com **duas linhas sobrepostas**: menor pedido visível (o que você
      pagaria agora) e mediana `median_low` (o preço típico). Os números batem com os do
      console `--mercado` para o mesmo instante: mesma fonte, mesma conta, **sem um segundo
      parser do CSV**.

- [ ] **DASH-04**: O valor de **agora** fica em destaque: quanto valem **5 milhões** de adena,
      em XM e em R$ — com `n` e **recência** ao lado, como todo número que sai na tela no
      `--mercado`. Com o scanner parado, o dashboard continua exibindo o último dado e diz de
      quando ele é; nunca afirma "agora" sobre um número velho.

      **A unidade mudou de 1 milhão para 5 milhões em 2026-09-03, e não foi esta fase que
      mudou.** Um `/gsd-quick` de outro chat (`f098f7a`, *"a taxa da adena passa a se falar por
      5 milhoes"*) trocou `UNIDADE_DA_TAXA` em 11 arquivos, com os testes junto, **antes** de a
      Fase 2 despachar — o executor da Fase 2 herdou a unidade já trocada, corretamente. A razão
      da troca é a que este projeto respeita: a coluna do jogo se chama literalmente
      `5 mln increment`, então 5 milhões é a unidade em que o usuário lê o preço na tela, e
      falar em 1 milhão obrigava a uma conversão mental que a própria tela não pede. **Fica
      registrado porque o texto anterior deste requisito, o goal da Fase 1 e os critérios de
      sucesso dela dizem "1 milhão", e a verificação da Fase 1 rodou contra aquela redação** —
      quem reler aqueles documentos vai encontrar a unidade antiga e precisa saber que ela caiu,
      e por quê, em vez de achar que o código divergiu do plano.

- [ ] **DASH-05**: A visualização é um **componente de série genérico**, e a Adena é a
      primeira instância — não um caso especial no código. Instanciar uma segunda série
      (qualquer item da aba de negociação) não exige código de gráfico novo. O v1 só mostra
      Adena na tela; a generalidade é provada em teste.

- [ ] **DASH-06**: O dashboard sobe por **lançador próprio** (`dashboard.bat`), em processo
      separado, e derrubar o dashboard não derruba a coleta da noite. O comportamento do
      `--mercado` fica **idêntico**, com **uma exceção nomeada e aprovada pelo usuário em
      2026-09-01**: `mercado_catalogo.py` troca `from .config import RAIZ` por um módulo folha
      `l2scanner/raiz.py`. A redação anterior dizia "byte-idêntico" e foi corrigida quando a
      pesquisa mediu o preço de mantê-la: sem esse corte, o dashboard carrega **280 módulos,
      44 MB e ~300 ms** de OpenCV e numpy que nunca usa — `config` era importado ali **só** por
      essa constante. Com o corte: **52 módulos, 17 MB, ~50 ms, zero pesado**, e `RAIZ ==
      raiz.RAIZ` verificado. A promessa que sobrevive é a que importa: **nenhuma mudança de
      comportamento no caminho da coleta**.

## Fase 2 — a calculadora de rotas de compra

- [ ] **CALC-01**: Para um item, o dashboard compara **duas rotas de compra** — comprar no
      mercado pagando em XM, ou comprar do NPC pagando em adena convertida pela taxa ao vivo —
      e diz qual sai mais barata **e por quanto**. A comparação é sobre o **unitário derivado
      em `Fraction`**, nunca `float`, e o arredondamento acontece só na formatação: um veredito
      que vira de lado por meio centavo é exatamente o defeito que essa disciplina impede.

- [ ] **CALC-02**: O preço do NPC **em adena é configuração**, escrita uma vez, porque não
      existe segunda fonte em tela para o scanner ler (decisão do usuário, 2026-09-02). Ele
      recebe o mesmo tratamento do câmbio XM→BRL: aparece declarado como **informado por você**,
      nunca como medido, e a tela diz **de onde ele veio e quando o programa o leu**.

      **Emenda de 2026-09-03, no planejamento da fase — a redação anterior dizia "informado por
      você *e quando*", pelo espelho do câmbio, e ela não é entregável como estava.** O
      `cambio.json` guarda um histórico com data porque **o programa o escreve**; o `config.toml`
      é escrito à mão e o programa não tem como saber quando aquele preço foi digitado. As três
      candidatas foram consideradas: (1) derivar o "quando" da data de modificação do arquivo —
      **recusada**, porque mexer em qualquer outra seção do mesmo arquivo mudaria a data sem
      ninguém ter tocado no preço, e a frase seria plausível e falsa ao mesmo tempo; (2) não
      exibir quando nenhum — **recusada**, porque descarta um fato que o programa sabe; (3) exibir
      o instante em que o dashboard **leu** a configuração no arranque — **adotada**. Ela é um
      fato do programa e responde à pergunta que esta fase cria: a configuração é lida uma vez, no
      arranque, então quem corrigir um preço e recarregar o navegador veria o número velho sem
      nenhum sinal. O que a tela **não** faz é chamar o instante da leitura de instante do
      informe: são dois fatos com nomes parecidos, e trocar um pelo outro é mentir com cara de
      número — a mesma armadilha que `recencia_do_preco` já documenta no `mercado_analise`.

- [ ] **CALC-03**: O **veredito não depende do câmbio XM→BRL**. As duas rotas terminam
      multiplicadas pelo mesmo `reais_por_xm`, que portanto cancela na comparação — "qual é mais
      barata" se responde tendo XM como denominador comum. Sem câmbio informado, o veredito
      **continua na tela** e só o "quanto em R$" desaparece, pela mesma regra ortogonal que a
      Fase 1 aplica ao cartão de R$.

- [ ] **CALC-04**: Abaixo do piso de evidência do item (os `N_MINIMO_*` que já existem no
      `mercado_analise`), a tela diz que **ainda não dá para responder**, com a frase de falta
      vinda do Python. Um veredito chutado sobre `n=1` seria pior que nenhum veredito: é uma
      afirmação sobre dinheiro com cara de conta feita.

- [ ] **CALC-05**: A calculadora é **genérica** — Gemstone C e Gemstone B são as duas primeiras
      instâncias, não casos especiais no código. Acrescentar um terceiro item é uma entrada de
      configuração, sem código novo de cálculo nem de tela, e isso é provado por teste. O
      casamento do item com a série do CSV reusa o `nome_normalizado` do `mercado_analise`
      (exato, com ambiguidade quebrando e listando as candidatas) — um segundo casamento
      inventado aqui faria a Gemstone B virar Gemstone C.

## Fase 3 — o item pela tela

- [ ] **ITEM-01**: O item se escolhe **pela tela**, com autocompletar sobre **as séries que o
      scanner já leu de verdade** — o nome exato vem do CSV, não da digitação do usuário. Isso
      remove **estruturalmente** a armadilha que ele encontrou em campo em 2026-09-04: o
      casamento é exato de propósito (similaridade juntaria Gemstone B com Gemstone C), então
      digitar `Gemstone C` onde o OCR gravou outra grafia produz a linha "nunca vi este item"
      com toda a razão — e parece defeito. Um item ainda não visto continua podendo ser digitado
      livre, e cai naquele mesmo estado: a caixa ajuda, não aprisiona.

- [ ] **ITEM-02**: Escolhido o item, a tela preenche **só o que o programa sabe**: nome exato,
      preço de mercado em XM, `n` e recência. **O preço do NPC e o tamanho do pacote nascem
      vazios.** Sugerir um valor "parecido" de outro item foi recusado explicitamente pelo
      usuário: um campo pré-preenchido é um campo que alguém esquece de conferir, e este decide
      compra com dinheiro real.

- [ ] **ITEM-03**: Um item salvo pela tela **persiste em JSON escrito pelo navegador**, e não no
      `config.toml`. O critério é o mesmo que já separou os dois arquivos neste workstream —
      **quem escreve**: o navegador escreve JSON, o humano escreve TOML, que tem comentário para
      anotar de qual NPC veio o preço. Reescrever o TOML pelo programa apagaria essa anotação.
      Os dois convivem, e o `config.toml` do usuário nunca é modificado por esta feature.

- [ ] **ITEM-04**: Existe um **modo simulação** que responde "e se o NPC cobrasse outro preço?"
      mudando o veredito **só na tela**, visivelmente marcado como simulação, e que **desaparece
      ao recarregar** sem ter tocado no que está salvo. A separação é estrutural, não uma flag:
      um número de teste que vaza para o disco vira um veredito errado amanhã, e essa é a pior
      saída possível desta fase.

- [ ] **ITEM-05**: Item salvo pela tela aparece **sem reiniciar**; item vindo do `config.toml`
      continua exigindo reinício — e **a tela diz de onde cada linha veio**. A assimetria não é
      escolha, é consequência medida: `config.toml` é lido uma vez no arranque
      (`dashboard.py:799`) e `ler_o_cambio` roda dentro do manipulador de requisição
      (`dashboard.py:543`). Sem a tela declarar isso, o usuário edita um arquivo, não vê mudar, e
      conclui que a feature quebrou.

## Restrições herdadas — valem no workstream inteiro

- **FIRE-01 continua valendo**: nenhuma biblioteca de síntese de input entra na árvore.
- **Doutrina de zero-install**: dependência nova é decisão de pesquisa com justificativa, não
  um `pip install` de conveniência. Foi o que manteve o `rich` fora do console de mercado.
- **O dashboard nunca lê o `calibration.json`** nem toca em captura de tela.
- **Nunca acoplar ao detector de morte** (`rastreador.py`, `visao.py`).
- **Falha fechada**: dado incompleto é descartado, nunca interpretado.
- **Nada de constante mágica**, e **um número que caiu precisa dizer que caiu**.

## Rastreabilidade

| ID | Fase | Estado |
|---|---|---|
| DASH-01 | Phase 1 | Pending |
| DASH-02 | Phase 1 | Pending |
| DASH-03 | Phase 1 | Pending |
| DASH-04 | Phase 1 | Pending |
| DASH-05 | Phase 1 | Pending |
| DASH-06 | Phase 1 | Pending |
| CALC-01 | Phase 2 | Pending |
| CALC-02 | Phase 2 | Pending |
| CALC-03 | Phase 2 | Pending |
| CALC-04 | Phase 2 | Pending |
| CALC-05 | Phase 2 | Pending |
| ITEM-01 | Phase 3 | Pending |
| ITEM-02 | Phase 3 | Pending |
| ITEM-03 | Phase 3 | Pending |
| ITEM-04 | Phase 3 | Pending |
| ITEM-05 | Phase 3 | Pending |
