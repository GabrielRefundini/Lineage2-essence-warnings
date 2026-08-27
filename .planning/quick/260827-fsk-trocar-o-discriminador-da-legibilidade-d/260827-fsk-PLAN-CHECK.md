# PLAN CHECK — quick 260827-fsk (trocar o discriminador da legibilidade da barra propria)

**Verdict: BLOCK** — 2 blockers, 5 warnings.

O plano e, em quase tudo, exemplar: cada numero da secao `<measured>` foi
REPRODUZIDO por este check contra os pixels reais do repositorio. O problema nao
esta nos numeros que ele mediu — esta no que ele NAO mediu, e sobre o que mesmo
assim concluiu.

## Reproducao independente dos numeros do plano

Rodado aqui, com a referencia de 20 valores da secao 8 e o casamento deslizante
descrito na Task 2:

| item | plano | medido neste check | bate? |
|---|---|---|---|
| `escuro_janela` HP (716,294) | moldura 86.42 / cas +0.944 | 86.42 / +0.944 | sim |
| `escuro_janela` MP (741,294) | moldura 29.08 / cas +0.964 | 29.08 / +0.964 | sim |
| `escuro_faixa[2:26]` igual a `escuro_cauda_vazia` | verdadeiro | verdadeiro | sim |
| dy -2..+2 | cas +0.964 constante; moldura 12.64..32.33 | identico | sim |
| coberta_1/2/3 | cas -0.059..+0.236 | 0.000 / 0.236 / 0.073 | sim |
| coberta_0 | cas +0.999, moldura 48.00 | +0.999 / 48.00 | sim |
| `quase_vazia_terreno_atras` | +0.979 | +0.979 | sim |
| varredura de painel (forward) | passa o limiar so em k=20, hp 10.47% | identico (0.676 em k=20) | sim |

`recordings/escuro_janela.png` existe (1392x1720, brilho 58.12), `recordings/`
esta mesmo no `.gitignore` com excecao para `tests/fixtures/`, e
`recordings/hp_baixo/` esta mesmo VAZIO. A Task 1 resgata a evidencia perecivel
ANTES de qualquer coisa depender dela — ordem correta.

---

## BLOCKER 1 — a afirmacao que sustenta o plano inteiro e FALSA: um painel que cobre o LADO ESQUERDO da barra passa no portao novo lendo 0% de HP

O plano afirma, e repete no threat model (T-fsk-02), no `must_haves` e no
`success_criteria`, que "nenhum composto passa no limiar 0.40 com leitura abaixo
de 10.47%" e portanto que "um painel de inventario nao consegue produzir morte
falsa atraves deste portao".

A varredura da secao 6 mede UMA UNICA DIRECAO: `livre_0[:, :k]` + `coberta[:, k:]`
— o painel cobrindo a DIREITA, deixando a esquerda da barra a mostra. Mas
`medir_barra` mede a CORRIDA INICIAL a partir da esquerda. A direcao que produz
`hp = 0.0` e exatamente a OUTRA: o painel cobrindo a ESQUERDA. Essa direcao nao
foi medida. Medida aqui, sobre os mesmos pixels reais
(`coberta_N[:, :k]` + `livre_0[:, k:]`):

| k coberto a esquerda | hp lido | desvio | moldura | veredito HOJE | veredito NOVO |
|---|---|---|---|---|---|
| 5 coberta_1 | **0.0000** | 35.58 | 48.92 | ILEGIVEL | **LEGIVEL** (cas 1.000) |
| 5 coberta_3 | **0.0000** | 35.60 | 55.42 | ILEGIVEL | **LEGIVEL** (cas 0.999) |
| 20 coberta_1 | **0.0000** | 33.36 | 48.92 | ILEGIVEL | **LEGIVEL** (cas 0.956) |
| 20 coberta_3 | **0.0000** | 32.89 | 55.42 | ILEGIVEL | **LEGIVEL** (cas 0.967) |
| 60 coberta_1 | **0.0000** | 34.52 | 48.92 | ILEGIVEL | **LEGIVEL** (cas 0.573) |
| 60 coberta_3 | **0.0000** | 33.69 | 55.42 | ILEGIVEL | **LEGIVEL** (cas 0.723) |

Leitura 0.0000 contra `fracao_hp_considerada_zero = 0.02`. Nao ha folga de 5.2x:
ha folga NEGATIVA. Esses compostos sao recusados HOJE (moldura 48.92 e 55.42,
ambas abaixo de 60) e passam a ser aceitos pelo portao novo — que e, letra por
letra, a classe de defeito que a quick `260826-dxm` pagou para matar: 27 mortes
falsas mais 27 ressurreicoes falsas.

Por que o casamento nao protege aqui: o perfil e a media por LINHA (`axis=1`).
Cobrir 5, 20 ou 60 colunas de 191 mal move a media de cada linha, e Pearson e
cego a escala. O discriminador e estruturalmente insensivel a oclusao parcial
pela esquerda — que e precisamente a oclusao que zera a leitura.

O calculo da margem da secao 7 herda o erro: "coberta maximo +0.236, folga 0.164"
so vale porque a amostra de cobertas contem apenas oclusao TOTAL e oclusao pela
direita. Com a direcao esquerda incluida, o maximo da classe coberta-que-le-0%
e +1.000. O limiar 0.40 nao separa nada nesse regime, e nenhum outro limiar
separaria — o mesmo argumento que o plano usa contra a moldura se aplica ao
casamento.

Fix, em ordem de custo: (a) tornar o braco novo do OR condicional a leitura — so
aceitar via casamento quando a leitura NAO estiver em regime de morte, o que
preserva integralmente o objetivo porque `escuro_cauda_vazia` le 88.5%; ou (b)
acrescentar ao portao um discriminador que enxergue oclusao das PRIMEIRAS
colunas (o canto esquerdo do TODO, que a Task 3 descarta por nao servir com a
barra em 0% — mas e exatamente aqui que ele serviria); ou (c) medir e reportar a
varredura REVERSA e reprojetar o limiar.

Nota separada: `coberta_2` composta pela esquerda ja passa HOJE (moldura 64.00,
acima de 60) lendo 0.0000. Buraco PRE-EXISTENTE, nao causado por este plano —
mas mostra que a familia "oclusao pela esquerda" nunca foi coberta por nenhum
dos dois portoes, e merece registro no TODO.

## BLOCKER 2 — o teste de seguranca proposto CERTIFICA a propriedade falsa

`TestOCustoMedidoDeAceitarACobertaParcial` (Task 2) monta a varredura exatamente
na direcao unica da secao 6. Ele passaria em verde e ficaria no repositorio como
prova documentada de que "painel de inventario nao produz morte falsa por este
portao" — afirmacao que este check acabou de falsificar sobre os mesmos pixels.
Um teste que prende a propriedade errada e pior que nenhum teste: e o proximo
leitor confiando nele.

Fix: a varredura tem que percorrer as DUAS direcoes, e a asercao tem que ser
sobre a LEITURA, nao sobre k — para todo composto cuja leitura fique em ou
abaixo de `fracao_hp_considerada_zero`, o portao recusa. Escrita assim, ela
falha hoje e passa a valer como a rede de seguranca que o plano quer que ela seja.

---

## Warnings

1. **O numero de dy=±3 do plano nao reproduz, e se contradiz.** O plano diz que
   "em dy=±3 o casamento cai para +0.376/+0.435 e o recorte volta a ser
   recusado" — mas 0.435 e MAIOR que o limiar 0.40, ou seja o proprio texto
   descreve um caso ACEITO chamando-o de recusado. Medido aqui: +0.293 nos dois
   lados (recusado, como o plano queria). Corrigir o texto e recolher o numero;
   este plano se apresenta como "nenhum numero e escolhido, todos sao lidos", e
   este saiu errado.

2. **±2 px e a tolerancia inteira, e nao ha rede alem dela.** Em dy=±3 o
   casamento (0.293) E a moldura (35.04 / 37.67) reprovam juntos: silencio. O
   plano chama isso de "comportamento certo", mas o TODO ja registra um caso
   real de desalinhamento por janela movida (`base_janela.png`). Nao e
   regressao — hoje dy=+1 ja reprova — mas o plano nao deveria vender ±2 px como
   robustez resolvida. Registrar no TODO como o segundo regime nao coberto.

3. **O verify de `pyproject.toml` e vacuo depois dos commits.**
   `git diff --name-only | grep -q pyproject.toml` olha so o nao-commitado, e a
   Task 2 manda commitar antes. Passa sempre. Usar `git diff --name-only` contra
   a base da branch.

4. **"MAIS testes do que comecou" nao tem verificacao automatizada.** A Task 2
   REMOVE `coberta_0` de duas parametrizacoes (-2 testes) e acrescenta classes
   novas. O `done` afirma o saldo positivo mas nenhum `<automated>` o mede.
   Acrescentar `--collect-only -q | tail -1` nas duas pontas.

5. **"8 de 8 cobertas" mistura duas populacoes.** `TestAsOitoFixturesReais...`
   parametriza sobre 4 fixtures versionadas; as outras 4 vem de
   `recordings/inv3/*_JANELA.png`, que e gitignored. Um clone limpo nunca prova
   as 8. Dizer isso explicitamente — a Task 2 ja faz o certo com `pytest.skip`
   para `inv2/`; fazer igual aqui.

## O que esta CORRETO e deve sobreviver a revisao

- **A honestidade sobre o TODO.** A Task 3 mantem o arquivo em `pending/`, com
  verify que falha se ele aparecer em `done/`, e a secao 10 declara sem rodeio o
  regime nunca observado (HP proprio baixo em terreno escuro, recorte inteiro de
  191 px). Conferido: `recordings/hp_baixo/` esta vazio. Atende a restricao dada.
- **A monotonia da legibilidade e real.** O OR so acrescenta aprovacao; nenhum
  recorte que hoje le para de ler. A afirmacao esta correta — mas cobre o lado
  errado do risco: o dano do BLOCKER 1 nao e leitura que some, e leitura que
  APARECE onde nao devia.
- **A ordem tracer-primeiro da Task 1**, resgatando as tres fixtures do arquivo
  gitignored antes que qualquer coisa dependa delas, com `escuro_faixa[2:26]`
  provando o proprio alinhamento. O `test $? -eq 1` distinguindo "falhou" de
  "nao coletou" e um cuidado raro e bem-vindo.
- **A invariancia a brilho** e genuinamente o discriminador certo para o defeito
  que o plano existe para consertar: +0.964 num recorte cuja moldura despencou
  para 29.08, reproduzido aqui.

## Recomendacao

Devolver ao planejador. O objetivo — parar de calar a barra legitima em terreno
escuro — esta certo, e o discriminador escolhido serve. O que falta e a metade
nao medida da varredura de seguranca, e uma clausula que impeca o braco novo de
aprovar um recorte que le zero.
