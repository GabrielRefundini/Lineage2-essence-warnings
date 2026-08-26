---
phase: quick-260826-dxm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/visao.py
  - tests/test_inventario_por_cima_da_barra_propria.py
  - tests/fixtures/barra_propria/quase_vazia_terreno_atras.png
  - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
autonomous: true
requirements: [QUICK-260826-dxm]

estimate:
  tokens: 60000
  raw_tokens: 30000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Um recorte da barra propria COBERTO pelo inventario e declarado ILEGIVEL: `barra_propria_legivel` devolve False para as quatro fixtures reais `coberta_0..3.png` (D-01, D-03)."
    - "Uma barra propria LIVRE continua LEGIVEL: `barra_propria_legivel` devolve True para as quatro fixtures reais `livre_0..3.png` e para as quatro `*__hp_proprio*.png` que a suite ja globa hoje (D-03)."
    - "O caminho do defeito deixou de existir de ponta a ponta: `extrair` sobre um frame cujo `extras['hp_proprio']` e uma fixture coberta devolve `Observacao.hp_proprio is None` (nunca `0.0`), e o rastreador alimentado com essa observacao 30 vezes emite ZERO evento de morte."
    - "O caminho da MORTE DE VERDADE segue vivo: um recorte real de barra quase vazia, com o terreno aparecendo atras dela, atravessa `barra_propria_legivel`, chega em `extrair` como `hp_proprio == 0.0` e o rastreador emite MORREU (RESTRICAO DURA)."
    - "Os dois testes rodam EM SERIE dentro de `barra_propria_legivel` — o desvio-padrao continua la e o teste de moldura e acrescentado, nao substituido (D-01)."
    - "O limiar da moldura e 60.0, com a medicao registrada no comentario ao lado da constante: coberto no maximo 48.92, livre/vazio no minimo 78.73 (D-02)."
    - "O risco de terreno escuro (barra vazia sobre chao escuro poderia cair abaixo do limiar e suprimir morte real) esta registrado como pendencia explicita, com a direcao do dano nomeada (D-04)."
    - "A suite inteira segue verde, sem o jogo aberto e sem rede — 760 testes coletados hoje (758 passando + 2 skipped), e nenhum deles muda de veredito por causa desta mudanca."
  artifacts:
    - "l2scanner/visao.py — `BRILHO_MINIMO_DA_MOLDURA_PROPRIA`, `_moldura_da_barra_propria` e o segundo portao dentro de `barra_propria_legivel`"
    - "tests/fixtures/barra_propria/quase_vazia_terreno_atras.png — recorte 191x24 de uma barra REAL quase vazia, a unica amostra de barra vazia alinhada que o repositorio tem"
    - "tests/test_inventario_por_cima_da_barra_propria.py — as 8 fixtures nos dois sentidos, o caminho de ponta a ponta nos dois sentidos e o tripwire do desvio-padrao"
    - ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md — a pendencia do terreno escuro"
  key_links:
    - "`barra_propria_legivel` -> `extrair` -> `Observacao.hp_proprio` -> `rastreador` — e a unica corrente do defeito: se o portao novo ficar so na visao e o teste nao atravessar ate o rastreador, o plano prova a coisa errada"
    - "`_moldura_da_barra_propria` <-> `_bordas_da_barra_intactas` — mesma ideia, POLARIDADE INVERTIDA (a party rejeita borda clara demais, a propria rejeita moldura escura demais). Sem comentario explicando, o proximo leitor 'conserta' o sinal e reabre o defeito"
    - "o portao de desvio-padrao <-> o portao de moldura — os dois EM SERIE. `np.full((8,120,3), 60)` da moldura exatamente 60.00 e so e rejeitado porque o desvio continua la; apagar o desvio reabre um buraco medido"
---

<objective>
Fechar o falso positivo mais volumoso do projeto: com o inventario aberto por cima
da barra de vida do proprio personagem, o scanner le 0% e anuncia
"YAZALAQUE MORREU". O `logs/scanner.log` real tem **27 mortes + 27 ressurreicoes**
desse defeito — mais que todos os alertas de party somados.

Purpose: `barra_propria_legivel` decide hoje so por desvio-padrao de cinza
(`DESVIO_MINIMO_DA_BARRA_PROPRIA = 3.0`). A GRADE DO INVENTARIO tem contraste de
sobra e PASSA; dai `medir_barra` devolve 0.0 e o rastreador converte em morte. As
barras da PARTY ja tem o remedio para exatamente esta classe de problema
(`_bordas_da_barra_intactas`, com o comentario "So some quando outra janela do
jogo — inventario, ficha do personagem, loja — e aberta por cima"). A barra
PROPRIA nunca ganhou o equivalente.

Output: um segundo portao de moldura em serie com o de desvio, uma fixture nova de
barra quase vazia real, e uma bateria de regressao que prende os dois sentidos —
o inventario nao vira morte, e a morte de verdade continua virando morte.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@l2scanner/visao.py
@tests/test_modo_solo.py
</context>

<decisoes_travadas>
As decisoes vieram do levantamento do usuario e NAO devem ser revisitadas. Os
identificadores abaixo sao usados nas tarefas para rastreio:

- **D-01** = (a) Acrescentar a `barra_propria_legivel` um teste de MOLDURA, no
  espirito do `_bordas_da_barra_intactas` que ja existe para a party. Manter
  TAMBEM o teste de desvio-padrao: os dois EM SERIE, nao um no lugar do outro.
- **D-02** = (b) O limiar da moldura fica entre 48.9 e 73.7. Escolher
  CONSERVADOR (perto de 60) e registrar a medicao no comentario — este
  repositorio documenta numero medido, nunca palpite.
- **D-03** = (c) As 8 fixtures reais viram regressao permanente: as 4 cobertas
  ILEGIVEIS, as 4 livres LEGIVEIS.
- **D-04** = (d) O risco de HP baixo precisa ficar documentado e, se possivel,
  TESTADO. Se a moldura escurecer com HP baixo, o remedio suprimiria MORTE REAL —
  o pior desfecho possivel neste projeto.

**RESTRICAO DURA:** o remedio NAO pode transformar o scanner num que deixa de
avisar morte de verdade. A morte real do proprio personagem acontece com a barra
VISIVEL — esse caminho precisa de teste.
</decisoes_travadas>

<medicoes>
Feitas no planejamento contra os pixels reais que ja estao no repositorio. **Nao
repetir a investigacao — repetir a MEDICAO nos testes.**

Definindo `moldura_min` = menor media de cinza entre as quatro bordas do recorte
(coluna 0, coluna -1, linha 0, linha -1):

| recorte 191x24 | col0 | col-1 | lin0 | lin-1 | **moldura_min** | desvio |
|---|---|---|---|---|---|---|
| `coberta_0.png` | 86.42 | 48.00 | 98.02 | 83.21 | **48.00** | 36.54 |
| `coberta_1.png` | 48.92 | 74.54 | 61.50 | 73.14 | **48.92** | 29.66 |
| `coberta_2.png` | 64.00 | 28.00 | 47.47 | 44.77 | **28.00** | 24.55 |
| `coberta_3.png` | 55.42 | 29.00 | 42.02 | 41.07 | **29.00** | 19.58 |
| `livre_0..3.png` | 86.42 | 91.92 | 104.57 | 87.79 | **86.42** | 35.18–35.47 |
| as 4 `*__hp_proprio*.png` ja globadas | 86.42 | 91.92 | 104.57 | 87.79 | **86.42** | 38.63 |
| **barra quase vazia (proxy, ver abaixo)** | 95.88 | 80.25 | 78.73 | 85.34 | **78.73** | 31.71 |

Da tela ao vivo do usuario (45 livres + 9 cobertas): livre 73.7–86.4, coberta
28.0–48.9.

**O desvio-padrao NAO separa, e isso esta medido dentro do repositorio:**
`coberta_0` da desvio **36.54**, MAIOR que `livre_0` (**35.47**). Qualquer limiar
de desvio que rejeite a coberta rejeita tambem a livre.

**A moldura separa limpo:** pior coberta **48.92**, pior livre/vazia **78.73**.
Vao de 29.8 pontos.

### Por que a POLARIDADE e invertida em relacao a party

`_bordas_da_barra_intactas` olha a coluna imediatamente FORA da barra da party
(`barra_x - 1` e `barra_x + largura`), onde o jogo desenha uma linha ESCURA de
chrome, e rejeita quando essa linha fica CLARA demais.

A regiao `hp_proprio` calibrada (esquerda 294, topo 716, 191x24) nao tem margem
sobrando: as quatro bordas do recorte caem DENTRO do campo da barra. Medido em
`livre_0.png`: **89.6% do recorte casa a mascara vermelha** e todas as quatro
bordas tem preenchimento. Entao a barra propria e CLARA — pelo vermelho quando
cheia, e pelo TERRENO que aparece atras quando vazia (a parte vazia e
transparente, coisa que o projeto ja documentou na Fase 2). O painel do
inventario, ao contrario, e um overlay ESCURO.

Logo: party rejeita borda CLARA demais; propria rejeita moldura ESCURA demais.
Isso precisa estar escrito no codigo, senao o proximo leitor "conserta" o sinal.

### D-04: o risco de HP baixo, MEDIDO em vez de so anotado

Confirmado no planejamento que **nenhuma amostra da barra propria alinhada e de HP
baixo** — as 8 fixtures, as 4 `*__hp_proprio*` e todos os frames de janela em
`recordings/` estao a 100% (o `recordings/base_janela.png`, que parecia HP baixo,
e na verdade a regiao DESALINHADA depois da janela ser movida; nao serve).

Existe, porem, um proxy real e melhor que qualquer sintetico: **a barra de MP do
proprio personagem**, no mesmo widget, mesma largura, mesmo chrome, em
`recordings/agora_janela.png` — ela esta em **170/2567 (6.6%)**, ou seja
praticamente VAZIA, com o terreno aparecendo atras de ~95% do comprimento dela.
Medido nesse recorte (191x24, esquerda 294, topo 741 — o campo do MP fica entre
as linhas escuras y=740 e y=765):

- `moldura_min` = **78.73** — dentro da faixa das LIVRES, longe das cobertas
- desvio = 31.71
- `medir_barra` com os limiares de **HP** sobre ele = **0.0%** (nao ha vermelho)

Ou seja: uma barra praticamente vazia deste widget continua CLARA, porque o vazio
mostra terreno. O remedio nao suprime a leitura de zero — e isso agora e um
numero, nao uma esperanca.

**Residual que sobra (vira pendencia, D-04):** o proxy foi medido sobre terreno de
grama (cinza ~95). Em masmorra escura ou a noite, o terreno atras da parte vazia
pode ficar abaixo de 60 e uma barra vazia de verdade seria declarada ILEGIVEL —
que e a direcao ruim do dano. Por isso o limiar vai no pe da faixa (60, e nao o
meio do vao medido, 63.8).
</medicoes>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: o caminho inteiro, nos dois sentidos, numa fatia so</name>
  <files>tests/fixtures/barra_propria/quase_vazia_terreno_atras.png, tests/test_inventario_por_cima_da_barra_propria.py, l2scanner/visao.py</files>
  <read_first>l2scanner/visao.py (`barra_propria_legivel`, `DESVIO_MINIMO_DA_BARRA_PROPRIA`, `_bordas_da_barra_intactas`, `medir_barra`, `extrair`), tests/test_modo_solo.py (a classe que ja exercita `barra_propria_legivel`, para reaproveitar o estilo e os helpers de montagem de `Frame`)</read_first>
  <behavior>
    O caminho que precisa deixar de existir:
    - `extrair` sobre um `Frame` cujo `extras['hp_proprio']` e `coberta_1.png`
      (e `coberta_2`, e `coberta_3`) devolve `Observacao.hp_proprio is None`.
      Hoje devolve `0.0` — as tres medem 0.0% e passam pelo portao atual.
    - Essa observacao, alimentada 30 vezes no rastreador em modo solo, emite
      ZERO evento de morte.

    O caminho que precisa continuar existindo (RESTRICAO DURA):
    - `extrair` sobre um `Frame` cujo `extras['hp_proprio']` e
      `quase_vazia_terreno_atras.png` devolve `hp_proprio == 0.0` — legivel E
      zerada.
    - Essa observacao, alimentada no rastreador em modo solo depois de frames
      vivos, emite MORREU.

    Este segundo grupo precisa estar VERDE antes da implementacao e continuar
    verde depois. Ele e a rede, nao o alvo.
  </behavior>
  <action>
    PRIMEIRO recortar a fixture, porque a fonte e descartavel: `recordings/` esta
    no `.gitignore` (linha 6) e some num `git clean`. Cortar
    `recordings/agora_janela.png[741:765, 294:485]` (191x24 — a barra de MP do
    proprio personagem, 170/2567) e gravar como
    `tests/fixtures/barra_propria/quase_vazia_terreno_atras.png`. **Nao** por
    `hp_proprio` no nome do arquivo: `tests/test_modo_solo.py` tem um glob
    `tests/fixtures/**/*hp_proprio*.png` que afirma "barra propria real", e este
    recorte e a barra de MP usada como PROXY. Conferir depois de gravar que o
    arquivo tem 191x24, `moldura_min == 78.73` e `medir_barra` com os limiares de
    HP == 0.0.

    Criar `tests/test_inventario_por_cima_da_barra_propria.py` com os quatro
    testes de ponta a ponta descritos em `<behavior>`, montando o `Frame` pelo
    mesmo caminho que os testes existentes usam (nada de parser paralelo: tem que
    atravessar `extrair` de verdade e o rastreador de verdade). Rodar e confirmar
    o VERMELHO pelo motivo certo — os tres testes do inventario falham dizendo
    `hp_proprio == 0.0`, e os do caminho da morte ja passam.

    So entao implementar em `l2scanner/visao.py`, per D-01 e D-02:
    - `BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0`, com a medicao no comentario ao
      lado: coberta no maximo 48.92, livre/vazia no minimo 78.73, vao de 29.8
      pontos, limiar no PE da faixa por causa do terreno escuro (D-04).
    - `_moldura_da_barra_propria(recorte) -> float`: menor media de cinza entre
      coluna 0, coluna -1, linha 0 e linha -1.
    - Dentro de `barra_propria_legivel`, o portao de moldura EM SERIE com o de
      desvio que ja existe — acrescentado, nunca no lugar dele (D-01).

    A docstring precisa dizer o PORQUE, no estilo do projeto, e precisa nomear a
    POLARIDADE INVERTIDA em relacao a `_bordas_da_barra_intactas` (a party rejeita
    borda CLARA demais porque olha o chrome escuro de FORA da barra; a propria
    rejeita moldura ESCURA demais porque as quatro bordas caem DENTRO do campo da
    barra, que e claro pelo vermelho quando cheia e pelo terreno quando vazia).
    Sem essa frase, o proximo leitor inverte o sinal e reabre o defeito.

    Duas armadilhas medidas, para nao serem descobertas do jeito ruim:
    (1) `np.full((8,120,3), 60)`, que `tests/test_modo_solo.py` afirma ILEGIVEL,
    da moldura exatamente 60.00 — passa no portao novo e so continua rejeitado
    porque o portao de desvio segue no lugar. Motivo concreto para D-01 existir.
    (2) o ruido `rng(7)` do teste "contraste e nao saturacao" da moldura 120.33 e
    segue LEGIVEL, como deve.
  </action>
  <verify>
    <automated>python -m pytest tests/test_inventario_por_cima_da_barra_propria.py tests/test_modo_solo.py -q</automated>
  </verify>
  <done>Os quatro testes de ponta a ponta passam: as tres fixtures cobertas dao `hp_proprio is None` e zero morte, e a barra quase vazia real da `hp_proprio == 0.0` e emite MORREU. `tests/test_modo_solo.py` segue integralmente verde.</done>
  <reversibility rating="reversible">Uma constante, uma funcao auxiliar e uma clausula a mais num `and`. Reverter e apagar o portao novo; as fixtures ficam e continuam valendo.</reversibility>
</task>

<task type="auto" tdd="true">
  <name>Task 2: a bateria de regressao das 8 fixtures e a pendencia do terreno escuro</name>
  <files>tests/test_inventario_por_cima_da_barra_propria.py, .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md</files>
  <read_first>tests/fixtures/barra_propria/ (as 8 fixtures reais), a tabela de `<medicoes>` deste plano</read_first>
  <behavior>
    - `coberta_0.png`, `coberta_1.png`, `coberta_2.png`, `coberta_3.png` ->
      `barra_propria_legivel` False, uma assercao por arquivo, com o nome do
      arquivo na mensagem de falha (D-03).
    - `livre_0.png`, `livre_1.png`, `livre_2.png`, `livre_3.png` ->
      `barra_propria_legivel` True (D-03).
    - Tripwire: o desvio-padrao SOZINHO nao separava. `coberta_0` tem desvio
      36.54 e `livre_0` tem 35.47 — a coberta tem MAIS contraste que a livre.
      O teste afirma as duas coisas ao mesmo tempo: que `coberta_0` passaria no
      portao de desvio isolado, e que o portao completo a rejeita. E o que
      impede alguem de apagar a moldura por achar que o desvio bastava.
    - `quase_vazia_terreno_atras.png` -> `barra_propria_legivel` True, com
      docstring dizendo que e a barra de MP servindo de PROXY, que e a unica
      amostra alinhada de barra quase vazia que o repositorio tem, e que todas as
      amostras de HP proprio estao a 100% (D-04).
  </behavior>
  <action>
    Acrescentar as classes de regressao ao arquivo de teste criado na Task 1. Cada
    docstring registra a MEDICAO que justifica o teste — numero medido, nunca
    adjetivo — no estilo que o repositorio ja usa ("Medido: desvio 38,6 contra
    0,00 do lixo").

    Registrar a pendencia em
    `.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md`,
    seguindo o formato dos arquivos que ja estao em `.planning/todos/pending/`.
    Ela precisa nomear a DIRECAO DO DANO, que e o que a torna diferente de uma
    anotacao qualquer: o portao supoe que a parte vazia da barra mostra terreno
    mais claro que 60; medido sobre grama deu 78.73; em masmorra escura ou a noite
    o terreno pode cair abaixo do limiar e uma barra vazia DE VERDADE seria
    declarada ilegivel — morte real suprimida, que e o pior desfecho deste
    projeto. Registrar tambem o que fecharia a pendencia: uma gravacao da propria
    barra com HP baixo em ambiente escuro, que hoje o repositorio nao tem.

    Por fim rodar a suite inteira e comparar com a linha de base: 760 testes
    coletados hoje (758 passando + 2 skipped). Nenhum teste existente pode mudar
    de veredito.
  </action>
  <verify>
    <automated>python -m pytest -q 2>&1 | tail -5</automated>
  </verify>
  <done>As 8 fixtures reais estao presas nos dois sentidos, o tripwire do desvio-padrao esta no lugar, a pendencia do terreno escuro esta registrada com a direcao do dano nomeada, e a suite inteira passa sem nenhum teste antigo mudando de veredito.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pixels da tela -> `visao.extrair` | unica entrada nao confiavel tocada aqui; e uma imagem local, ja capturada, sem rede e sem entrada de usuario |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260826-01 | Denial of Service | `barra_propria_legivel` — portao novo | high | mitigate | O modo de falha real do projeto: um portao apertado demais cala o aviso de morte. Mitigado por medicao (proxy de barra vazia real da 78.73, contra limiar 60) e por teste dedicado do caminho da morte na Task 1 |
| T-260826-02 | Information Disclosure | fixture `quase_vazia_terreno_atras.png` | low | accept | Recorte de 191x24 de UI de jogo, sem nome de conta, sem token, sem dado pessoal. As 8 fixtures irmas ja estao no repositorio pelo mesmo criterio |
| T-260826-03 | Tampering | instalacao de pacotes | low | accept | Nenhuma dependencia nova. Tudo usa `cv2` e `numpy`, que ja sao do projeto — o portao de legitimidade de pacote nao se aplica |
</threat_model>

<verification>
1. `python -m pytest -q` — suite inteira verde, sem o jogo aberto e sem rede.
2. Contagem: 760 testes coletados na linha de base; nenhum teste existente muda
   de veredito.
3. `git status` — `tests/fixtures/barra_propria/quase_vazia_terreno_atras.png`
   rastreado (a fonte em `recordings/` e ignorada e nao pode ser a fonte da
   verdade).
4. Leitura do diff de `l2scanner/visao.py`: o portao de desvio continua la, o de
   moldura foi acrescentado EM SERIE, e a constante carrega a medicao no
   comentario.
</verification>

<success_criteria>
- As 4 fixtures cobertas: ILEGIVEIS. As 4 livres: LEGIVEIS.
- `extrair` com um recorte coberto: `hp_proprio is None`, nunca `0.0`.
- 30 observacoes de barra coberta no rastreador: ZERO evento de morte.
- Uma barra real quase vazia: LEGIVEL, `hp_proprio == 0.0`, e o rastreador emite
  MORREU — a restricao dura, com teste.
- O limiar 60.0 tem a medicao ao lado, e a polaridade invertida em relacao a
  `_bordas_da_barra_intactas` esta explicada por escrito.
- A pendencia do terreno escuro esta registrada com a direcao do dano nomeada.
</success_criteria>

<output>
Create `.planning/quick/260826-dxm-inventario-por-cima-da-propria-barra-vir/260826-dxm-SUMMARY.md` when done
</output>
