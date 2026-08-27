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

---

# PLAN CHECK — ITERACAO 2 (revisao 2 do plano, commit 7e24e80)

**Verdict: BLOCK** — 1 blocker novo, 2 warnings novos. Os DOIS blockers da
iteracao 1 estao **CLOSED**.

O redesenho esta certo e a prova esta certa. O blocker novo nao esta no portao:
esta no que a leitura recem-liberada faz na CAMADA DE CIMA — um caminho que o
plano nao modela, o pre-voo nao ve e os testes propostos nao cobrem.

## Reproducao independente da revisao 2

| item | plano | medido neste check | bate? |
|---|---|---|---|
| `escuro_janela` 1392x1720, brilho 58.12 | idem | idem | sim |
| HP (716,294) | moldura 86.42 / cas +0.944 | 86.42 / +0.944 | sim |
| MP (741,294) | moldura 29.08 / cas +0.964 | 29.08 / +0.964 | sim |
| `escuro_faixa[2:26] == escuro_cauda_vazia` | verdadeiro | verdadeiro | sim |
| leitura do MP com `limiares_mp` | 0.8848 | 0.8848 | sim |
| 3b, painel a ESQUERDA, k=5/20/60/120 | leitura 0.0000; moldura 48.92/64.00/55.42 | identico | sim |
| 4, a colisao | genuina +0.627 contra 5-col-esq +0.645 | 0.627 contra 0.622/0.619/**0.645** | sim |
| 4, k=3 e k=10 | +0.642 / +0.637 | idem | sim |
| 5, exaustao | 2304 compostos, 1733 em regime de morte, **0 aceitos** | **2304 / 1733 / 0**, 0.06 s | sim |
| 8, dy -4..+4 | +-2 constante +0.964; +-3 = +0.293/+0.364 | identico | sim |
| baseline de coleta | 1127 | 1127 | sim |
| `9d5533e` ancestral de HEAD | implicito | verdadeiro | sim |

Os quatro pontos encarregados a esta re-review:

1. **O portao usa a MESMA grandeza que o rastreador.** Confirmado no caminho de
   codigo: a Task 2 manda `extrair` MEDIR uma unica vez, com `cal.limiares_hp`
   sobre a regiao inteira, e entregar esse mesmo float ao portao E a
   `hp_proprio`. Nao ha segundo calculo, nao ha short-circuit, nao ha ordenacao
   em que o gate e o rastreador possam divergir. `0.05 > 0.02` e verdade por
   construcao. Unico residual, declarado pelo proprio plano: o braco de MOLDURA
   segue podendo certificar leitura zero — o buraco pre-existente, item 4.
2. **Exaustao reproduzida** nas duas direcoes, com o preenchimento de direita
   escuro: 2304 / 1733 / **zero aceitos**. A varredura nao e vazia.
3. **A intercalacao e real e esta dita sem enfeite** — plano secao 4 e truth 7,
   TODO item (4) da Task 3, e o bloco de output exigindo o mesmo do SUMMARY. Os
   tres com o numero. A promessa encolhida NAO esta enterrada: esta na revisao,
   no objective e no success_criteria.
4. **Buraco pre-existente confirmado:** `coberta_2[:, :5] + livre_0[:, 5:]` le
   0.0000 com moldura **64.00** (acima de 60) — aceito HOJE. Nao e criado nem
   fechado por esta mudanca. Registrado em tres lugares duraveis (TODO item 5,
   T-fsk-05, `TestOBuracoPreExistenteDoBracoDeMoldura`), com o candidato
   (`sobra`: 0 nas 51 genuinas contra 11..186 nos compostos) e a condicao de
   adocao (medir contra TERRENO VERMELHO, porque o modo de falha e silencio).

## Blockers da iteracao 1

- **BLOCKER 1 (oclusao pela esquerda passando lendo 0%) — CLOSED.** Resolvido por
  construcao e nao por limiar; re-medido, zero aceitos em 1733.
- **BLOCKER 2 (o teste certificava a propriedade falsa) — CLOSED.** A varredura
  percorre as duas direcoes, aserta sobre a LEITURA e nao sobre k, e a classe
  aserta que o conjunto em regime de morte nao e vazio.

## BLOCKER NOVO — aceitar `coberta_0` abre um alerta falso de VOCE_SEM_PARTY, e isso nao esta no plano

O plano contabiliza o custo de aceitar a coberta parcial como UMA coisa so:
"`coberta_0` passa a ler 86.91% e nao pode virar morte porque fica 43x acima do
limiar de morte" (Task 3 item 7 e `TestOCustoDeAceitarACobertaParcial`). Isso e
verdade sobre a MORTE — e o limiar de morte e o unico consumidor de `hp_proprio`
que o plano examinou. Nao e o unico que existe.

`rastreador.py:454` ramifica em `obs.hp_proprio is not None and not modo_solo`
para `_avaliar_se_voce_esta_em_party`. HOJE, com o inventario por cima,
`hp_proprio` sai `None` e esse ramo nem e ENTRADO. Depois da mudanca ele passa a
ser entrado com 0.8691, e a guarda de cegueira de `rastreador.py:643` NAO salva,
porque ela so congela quando `hp_proprio` esta ZERADO. Com a party window coberta
pelo mesmo painel (`ui_visivel=False`), `_contador_sem_party` avanca a cada tick
e, em `confirmacoes_para_voce_sem_party = 8`, sai `VOCE_SEM_PARTY`.

Simulado aqui, com o portao forcado a aceitar `coberta_0` — que ele aceita:
leitura 0.8691 acima de 0.05 e casamento +0.999 acima de 0.40:

    HOJE     hp_proprio: None       -> ramo nao entrado, nenhum evento
    DEPOIS   hp_proprio: 0.8691, ui_visivel: False
             rastreador FRIO  -> nenhum evento (o comeco frio protege)
             rastreador MORNO -> tick 7: EVENTO VOCE_SEM_PARTY

MORNO e o estado NORMAL: `_voce_em_party=True` e `_ja_viu_party_window=True` sao
o que qualquer sessao em party tem depois do primeiro minuto. Oito ticks de
inventario aberto e coisa banal — e a familia de defeito e exatamente a que a
quick `260826-dxm` pagou para matar: alerta falso originado do painel do
inventario.

Por que nem o pre-voo nem os testes planejados pegam isto: o pre-voo roda a suite
inteira, e NENHUM teste da suite leva `coberta_0` ate o `Rastreador` — conferido,
`coberta_0` so aparece em `test_inventario_por_cima_da_barra_propria.py`, sempre
em chamada direta a `barra_propria_legivel` ou `extrair`. E
`TestOCustoDeAceitarACobertaParcial`, como escrita, aserta apenas que a leitura
fica acima do limiar de morte — a asercao reduzida que faz o custo PARECER
fechado.

Isto deixa imprecisas, como escritas, a truth 4 ("nenhuma oclusao passa a produzir
morte" — verdadeira sobre morte, silenciosa sobre este evento), o T-fsk-02 e o
success_criteria.

Fix, em ordem de custo:

(a) **Medir primeiro.** Acrescentar a `TestOCustoDeAceitarACobertaParcial` um
    percurso pelo `Rastreador` MORNO (`_voce_em_party=True`,
    `_ja_viu_party_window=True`) com `extrair(frame_solo("coberta_0"))` repetido
    por `confirmacoes_para_voce_sem_party + 2` ticks, exigindo lista de eventos
    VAZIA. Se ela nao for vazia — e nao e — o custo fica medido e a decisao vira
    explicita em vez de tacita.

(b) Se confirmar, escolher uma saida: estender a guarda de `rastreador.py:643`
    para congelar tambem quando a UI esta invisivel e a leitura veio do braco
    novo; ou expor na `Observacao` por qual braco a legibilidade passou; ou
    aceitar o alerta e registra-lo no TODO com o mesmo rigor do buraco
    pre-existente. Qualquer das tres serve. O que NAO serve e o plano seguir
    afirmando que o unico custo de `coberta_0` e uma leitura que nao pode virar
    morte.

Direcao do dano: alarme FALSO, nao silencio — nao e o defeito inaceitavel
declarado do projeto. Mas e NOVO, e causado por esta mudanca, e chega ao usuario
em 8 segundos de inventario aberto.

## Warnings da iteracao 1 — todos verificados

1. **dy=+-3 — CLOSED.** +0.293 / +0.364 re-medidos, ambos abaixo de 0.40, e a
   secao 8 traz a correcao NOMEADA, explicando que a linha antiga vinha do
   recorte de HP e nao do de MP.
2. **+-2 px e o teto — CLOSED.** Secao 10.4 e TODO item (6), sem vender robustez.
3. **`pyproject` — CLOSED com residual info.** O diff contra `9d5533e..HEAD`
   funciona (`9d5533e` conferido como ancestral de HEAD) e nao e mais vacuo.
   Residual: so ve o COMMITADO. Como o verify roda pos-commit, aceitavel.
4. **Contagem de testes — CLOSED e verificada por execucao.** Rodei o proprio
   comando da Task 2 no estado atual: imprime `coletados: 1127` e **sai 1**. O
   gate REPROVA no baseline, como o planejador afirma. Confirmei tambem que
   pytest devolve **4** para classe inexistente, validando o `test $? -eq 1` da
   Task 1.
5. **Duas populacoes (versionadas contra `recordings/`) — CLOSED.** A Task 2 manda
   pular com `pytest.skip` para `inv2/` e o mesmo cuidado para as 4 de `inv3/`.

## Warnings novos

1. **`2 skipped` esta escrito como se fosse constante.** Com os skips novos, um
   clone limpo (sem `recordings/`) tera MAIS de 2 skips, e a truth e o done dizem
   "pelo menos 1125 passed, 2 skipped". Nenhum verify automatizado aserta o
   numero de skips, entao nada quebra — mas o texto deveria dizer "2 skipped na
   maquina com `recordings/`, mais num clone limpo".
2. **Um dos tres preenchimentos de direita da varredura e SINTETICO.** A cauda
   escura e ladrilhada ate 191 colunas. O plano chama tudo de composto o tempo
   todo, mas a truth 3 diz "2304 compostos de painel REAL": os paineis sao reais,
   um dos tres preenchimentos de direita nao e. Uma palavra a corrigir, nao um
   defeito.

## Recomendacao

Devolver ao planejador. Falta UMA coisa: medir o que a leitura liberada faz no
RASTREADOR, e nao so contra o limiar de morte. O redesenho, a exaustao, a
promessa encolhida e o registro do que nao fecha estao todos corretos e todos
reproduzidos — este plano e mais honesto que o anterior e entrega menos de
proposito, o que e a troca certa. O que resta e CONTABILIDADE DE CUSTO, e o teste
que o expoe cabe em dez linhas dentro de uma classe que o plano ja tem.
