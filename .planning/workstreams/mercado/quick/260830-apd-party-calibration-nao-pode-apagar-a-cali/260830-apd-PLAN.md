---
phase: quick-260830-apd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/calibrar.py
  - tests/test_calibrar_nao_apaga_mercado.py
autonomous: true
requirements: [JANELA-13, CR-04-PARTY]

estimate:
  tokens: 62000
  raw_tokens: 62000
  tasks: 3
  confidence: low   # .planning/estimation-calibration.json tem samples: [] — fator 1.0, sem historico

must_haves:
  truths:
    - "Rodar a calibracao de party (`--auto` OU `--selecionar`) sobre um calibration.json que ja tem dados de mercado deixa os 27 campos que a party NAO possui byte a byte identicos ao que estava gravado."
    - "Os 13 campos que a party possui continuam recebendo exatamente o valor que a party grava hoje: sem `--nomes`, `nomes` volta a `[]` e `assinaturas` volta a `[]`; sem barra propria encontrada, `hp_proprio` volta a `None`."
    - "Um calibration.json ilegivel (corrompido ou de outra versao) NAO impede a party de gravar — ela grava e avisa ALTO, nomeando o que nao conseguiu preservar."
    - "O caminho `--solo` continua preservando o mercado, e agora existe teste afirmando isso."
    - "O teste falha no codigo de HOJE pela ausencia do dado de mercado, e passa depois do conserto."
    - "VERSAO_DO_ESQUEMA segue em 2 e o calibration.json REAL da raiz do repositorio termina com o mesmo digest com que comecou."
  artifacts:
    - "l2scanner/calibrar.py com `CAMPOS_DA_PARTY` e `fundir_com_a_calibracao_em_disco`"
    - "tests/test_calibrar_nao_apaga_mercado.py"
  key_links:
    - "O SEAM UNICO: `fundir_com_a_calibracao_em_disco` chamada imediatamente antes do `cal.salvar` final de `main()` — o unico ponto por onde `--auto`, `--selecionar` e `_tentar_pelas_janelas_do_jogo` passam, porque os tres constroem o objeto pela mesma `calibrar_automatico`."
    - "A lista de campos preservados e obtida por SUBTRACAO de `dataclasses.fields(Calibracao)` menos `CAMPOS_DA_PARTY` — campo novo nasce PRESERVADO, e nao apagado. E o sentido fail-safe da regra."
    - "`monkeypatch.setattr(l2scanner.calibrar, \"ARQUIVO_CALIBRACAO\", tmp_path / ...)` — e o unico mecanismo que mantem o calibration.json real do usuario fora do alcance do teste."
---

<objective>
Impedir que a calibracao de PARTY apague a calibracao de MERCADO do
`calibration.json` — um defeito medido em campo hoje (2026-08-30), que custou
13 moldes de glifo, 3 ancoras, a grade e um limiar.

Purpose: o incidente ja foi remediado a mao (resgate em
`calibration.RESGATE-13-glifos.json`, calibracao reinstalada). O que falta e
impedir a REPETICAO — e o motivo de ele ter existido e que nao havia teste
afirmando a invariante. O mesmo defeito foi consertado do lado do mercado
(CR-04) e ficou aberto do lado da party justamente porque nada o prendia.

Output: um seam de fusao em `l2scanner/calibrar.py` que espelha o desenho ja
usado em `calibrar_mercado.calibrar` (carrega → muta so o que e seu → grava), e
um teste que dirige o `main()` de verdade e falha no codigo de hoje.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.claude/CLAUDE.md
@.planning/workstreams/mercado/STATE.md
@l2scanner/calibrar.py
@l2scanner/calibracao.py
</context>

<o_que_eu_medi_antes_de_planejar>

Nada abaixo e leitura de codigo apenas; os dois primeiros itens foram
EXECUTADOS num diretorio temporario, com o `calibration.json` real intocado.

**1. Os tres pontos de gravacao, investigados um a um (o brief pediu os tres):**

| linha | funcao | de onde vem o `cal` | veredito |
|---|---|---|---|
| 1020 | `calibrar_tiat` | `Calibracao.carregar(ARQUIVO_CALIBRACAO)`, linha ~972 | **JA CORRETO** — load-mutate-save. Nao tocar. |
| 1112 | `main()`, ramo `--solo` | `calibrar_so_a_propria_barra` faz `Calibracao.carregar`, linha ~905 | **JA CORRETO** — load-mutate-save. Nao tocar. |
| 1244 | `main()`, ramo `--auto` / `--selecionar` | `calibrar_automatico` (linha 353) monta `Calibracao(...)` do zero | **E O DEFEITO.** |

Consertar so o 1244 NAO deixa a armadilha meio armada: os dois de cima ja fazem
o que o conserto faria. Mexer neles seria "consertar" o que esta certo.

**Os TRES caminhos de entrada convergem num unico seam.** `--auto` chama
`calibrar_automatico`; `--selecionar` chama `calibrar_selecionando`, que delega
para `calibrar_automatico`; e `_tentar_pelas_janelas_do_jogo` tambem delega para
`calibrar_automatico`. Os tres caem no mesmo `cal.salvar` da linha 1244. Um
seam, tres caminhos cobertos.

**Os `.bat`, conferidos:** `calibrar.bat` chama `--auto` (defeituoso),
`calibrar-solo.bat` chama `--solo` (ja seguro), `calibrar-tiat.bat` chama
`--tiat` (ja seguro), `calibrar-mercado.bat` chama outro modulo (ja consertado).
O modo solo NAO constroi do zero — ele entra no escopo apenas como teste de
regressao (Task 3), nao como conserto.

**2. A reproducao, EXECUTADA (esta e a resposta a "como voce confirmou que
falha hoje"):** um script dirigiu o `main()` de verdade com `--auto`, com
`ARQUIVO_CALIBRACAO` apontado para um arquivo temporario semeado com 10 moldes
de digito, 1 ancora, grade, `mercado_limiar_de_glifo` e `tiat_chat`. Saida
medida:

```
ANTES  : 10 moldes
rc     : 0
DEPOIS : 0 moldes
ancoras: None
grade  : None
glifo  : None
tiat   : None
```

Confirma o mecanismo E confirma que o harness do teste e viavel: 6
monkeypatches (`ARQUIVO_CALIBRACAO`, `capturar_tela`, `calibrar_automatico`,
`janela_que_contem`, `achar_barra_do_proprio`, `conferir_visualmente`) mais
`sys.argv`. Nenhuma janela do cv2 abre no caminho `--auto`.

**Descoberta que o brief nao previa e que ALARGA o dano medido:** `tiat_chat` e
`tiat_alvo` tambem sao apagados. Sao gravados por `calibrar-tiat.bat`, uma
ferramenta separada, e a party os destroi pelo MESMO mecanismo. `banner_manutencao`
tambem. Nao e escopo novo: o conserto correto os preserva de graca, e uma lista
que preservasse SO os `mercado_*` seria a armadilha rearmada para o proximo campo.

**3. A contagem de campos, extraida de `dataclasses.fields(Calibracao)`:** 40
campos. 13 sao da party (`party_window`, `ancora`, `layout`, `limiares_hp`,
`limiares_mp`, `geometria_da_tela`, `hp_proprio`, `nome_proprio`, `nomes`,
`assinaturas`, `janela`, `party_window_na_janela`, `versao`). Os outros 27 sao
os 24 `mercado_*` mais `banner_manutencao`, `tiat_chat` e `tiat_alvo`.

**4. Por que a lista e de DONOS e nao de PRESERVADOS.** Uma lista de campos a
preservar exige que quem adicionar o proximo campo opcional se lembre de
inscreve-lo — e o esquecimento reproduz o incidente. Uma lista de DONOS deixa o
campo novo preservado por omissao. O default de um campo desconhecido tem de ser
SOBREVIVER, nunca ser apagado.

**5. Por que NAO fundir dentro de `Calibracao.salvar`.** `salvar` e herdada por
`calibrar_mercado`, que ja carrega antes; fundir la faria a fusao acontecer duas
vezes e tornaria invisivel, para quem le `main()`, que existe uma leitura de
disco. O seam fica onde o defeito esta.

**6. Precedente de teste que ja existe no repositorio:**
`tests/test_calibrar_mercado.py:234` ja faz
`monkeypatch.setattr(l2scanner.calibrar, "calibrar_automatico", nunca)`. O
harness da Task 1 e esse idioma, com mais alvos.

</o_que_eu_medi_antes_de_planejar>

<auditoria_de_cobertura>

Nao ha ROADMAP/REQUIREMENTS/RESEARCH/CONTEXT para esta quick task: a fonte e o
brief. Cada item dele, mapeado:

| Fonte | Item | Onde e coberto |
|---|---|---|
| BRIEF | Consertar a perda: party apaga mercado | Task 2 |
| BRIEF | Espelhar o desenho de `calibrar_mercado.py:2676` (carrega → muta → grava) | Task 2 |
| BRIEF | Investigar os TRES pontos de gravacao, e dizer quais ja estao certos | `<o_que_eu_medi_antes_de_planejar>` item 1 + Task 2 (gate que prova que os outros dois nao foram tocados) |
| BRIEF | Conferir se o modo solo tambem constroi do zero | Item 1: NAO constroi. Entra so como teste de regressao (Task 3) |
| BRIEF | Teste em diretorio temporario, nunca no calibration.json real | Task 1 (`tmp_path` + monkeypatch de `ARQUIVO_CALIBRACAO`) + gate de digest em `<verification>` |
| BRIEF | Assercao que falha hoje e passa depois, com a confirmacao escrita | Task 1 (`<verify>` exige saida vermelha) + item 2 acima, medido |
| BRIEF | Cobrir os tres pontos por teste, ou dizer qual e por que | Task 3: `--auto` e `--selecionar` cobertos (Task 1), `--solo` coberto (Task 3), `--tiat` deixado de fora por CUSTO (tres monkeypatches a mais) e nao por impossibilidade, ja sendo load-mutate-save comprovado por leitura — motivo escrito na docstring do teste |
| BRIEF | Nunca bump de VERSAO_DO_ESQUEMA | Gate em Task 2 |
| BRIEF | Nao mexer em `rastreador.py` nem no portao de brilho de `visao.py` | Nenhuma task os lista em `<files>`; gate em `<verification>` |
| BRIEF | FIRE-01: nenhuma lib de sintese de input | Nenhuma dependencia nova em nenhuma task; `tests/test_firewall_escopo.py` roda na suite completa |
| BRIEF | Nao alterar o comportamento da calibracao de party em si | Task 1 caso 3 e Task 2 (a fusao devolve o valor NOVO para os 13 campos da party) |

Nenhum item ficou sem plano.

</auditoria_de_cobertura>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: O teste que falha hoje — o caminho de gravacao da party dirigido de ponta a ponta</name>

  <read_first>
    - `l2scanner/calibrar.py:1049-1287` (`main()` inteiro: o parse de argumentos, os tres ramos e o `cal.salvar` final)
    - `l2scanner/calibrar.py:281-355` (`calibrar_automatico`, onde o objeto novo nasce) e `620-635` (`calibrar_selecionando`, que delega para ele)
    - `l2scanner/calibracao.py:145-441` (a lista de campos da dataclass `Calibracao`) e `514-605` (`salvar`) e `606-716` (`carregar`)
    - `tests/test_calibrar_mercado.py:225-240` — o idioma de `monkeypatch.setattr(l2scanner.calibrar, ...)` que ja existe no repositorio
  </read_first>

  <files>tests/test_calibrar_nao_apaga_mercado.py</files>

  <behavior>
    Casos, todos contra um `calibration.json` que vive em `tmp_path`:

    - Caso 1 — `--auto` preserva: semear o arquivo com os 27 campos que a party
      NAO possui, todos preenchidos com valores distinguiveis (13 moldes de
      digito, 3 ancoras, grade, os quatro dicts de coluna, o cabecalho, cada um
      dos limiares, `banner_manutencao`, `tiat_chat`, `tiat_alvo`). Rodar
      `main()` com `--auto`. Para CADA um dos 27, o valor no JSON resultante e
      igual ao semeado. A comparacao e sobre o dict CRU de `json.loads`, e nao
      sobre o objeto reconstruido — e assim que "byte a byte" fica afirmado.
    - Caso 2 — `--selecionar` passa pelo mesmo portao: identico ao caso 1, com
      `calibrar_selecionando` monkeypatchado e `sys.argv` levando `--selecionar`.
    - Caso 3 — GUARDA DE REGRESSAO, verde nos dois lados: os 13 campos da party
      recebem o valor NOVO, e nao o do disco. Semear o arquivo com valores de
      party DIFERENTES dos que a rodada vai produzir (`party_window` noutro
      lugar, `nomes=["Antigo"]`, uma `assinaturas` de verdade, `hp_proprio`
      preenchido, `nome_proprio`, `janela`, `party_window_na_janela`). Depois de
      rodar sem `--nomes` e com `achar_barra_do_proprio` devolvendo `None`:
      `party_window`/`ancora`/`layout`/`geometria_da_tela` sao os NOVOS;
      `nomes == []`; `assinaturas == []`; `hp_proprio`, `nome_proprio`, `janela`
      e `party_window_na_janela` sao `None`.

      **ESTE CASO PASSA NO RED, E ISSO E O ESPERADO — NAO O ALTERE PARA
      FICAR VERMELHO.** O codigo de hoje monta a `Calibracao` do zero, entao
      esses 13 campos JA sao os novos; nao ha o que ele possa denunciar antes do
      conserto. Ele nao existe para provar o defeito, existe para impedir que o
      CONSERTO vire regressao: um load-mutate-save ingenuo faria `nomes`,
      `assinaturas` e `hp_proprio` velhos sobreviverem a uma recalibracao, e
      assinatura estale contra geometria nova e o modo de falha que manda a
      party socorrer a pessoa errada. A unica forma de deixa-lo vermelho no RED
      seria misturar afirmacao de mercado dentro dele — o que destroi
      exatamente o que ele guarda. Se ele passar na primeira rodada, siga em
      frente.
    - Caso 4 — a lista de donos e coerente com a dataclass: `CAMPOS_DA_PARTY` e
      subconjunto de `{f.name for f in fields(Calibracao)}` (pega renomeacao e
      erro de digitacao), e NENHUM campo com prefixo `mercado_` esta dentro
      dela — computado por prefixo, para um campo de mercado criado amanha
      entrar na afirmacao sozinho.
    - Caso 5 — arquivo ilegivel nao trava a party: semear um JSON corrompido,
      rodar `--auto`, e exigir codigo de retorno 0, o arquivo contendo a
      calibracao nova, e a saida do console contendo o aviso alto.

    A LEITURA DO RED, caso a caso — o executor conferir contra esta tabela
    antes de concluir que algo esta errado:

    | caso | no RED | por que |
    |---|---|---|
    | 1 | VERMELHO pelo dado ausente, a mensagem nomeia `mercado_templates_de_digito` | e a assercao que prende o defeito |
    | 2 | VERMELHO pelo mesmo motivo | mesmo defeito por `--selecionar` |
    | 3 | **VERDE, e esperado** | guarda de regressao; ver o bloco em maiusculas acima |
    | 4 | VERMELHO por `AttributeError` em `CAMPOS_DA_PARTY` | a constante ainda nao existe |
    | 5 | VERMELHO pela ausencia do aviso alto | o ramo de arquivo ilegivel ainda nao existe |

    Nenhum caso deve ser reescrito para mudar a cor dele nesta tabela. O portao
    do `<verify>` e satisfeito pelos casos 1 e 2 sozinhos: eles dao o codigo de
    retorno nao-zero E o nome do campo de mercado na saida. Registrar a saida
    vermelha inteira no SUMMARY.
  </behavior>

  <action>
    Criar `tests/test_calibrar_nao_apaga_mercado.py`.

    A docstring do modulo abre com o incidente medido em 2026-08-30 (13 moldes,
    3 ancoras, grade e limiar perdidos numa rodada de `calibrar.bat`), diz que o
    mesmo defeito ja tinha sido consertado do lado do mercado como CR-04, e
    registra o que este arquivo NAO alcanca, e pelo motivo VERDADEIRO: o
    caminho `--tiat` nao esta coberto por CUSTO, e nao por impossibilidade. Ele
    e alcancavel pelo mesmo idioma do caso 6 — `JanelaSource` falso — mais dois
    seams interativos (`_selecionar_regiao`, chamada duas vezes) e o
    `_gravar_conferencia`. O que dispensa o caso e outra coisa: `calibrar_tiat`
    ja e load-mutate-save comprovado por leitura, chamando
    `Calibracao.carregar(ARQUIVO_CALIBRACAO)` na primeira linha util da funcao,
    entao o caso seria guarda de regressao e nao prova de conserto. Escrever na
    docstring exatamente esses dois fatos — o custo e a comprovacao por leitura
    — para que quem quiser acrescentar o caso 7 saiba que sao tres monkeypatches
    a mais, e nao um obstaculo.

    Escrever tres auxiliares no topo:

    `_nova_party(geo)` devolve uma `Calibracao` so com os campos da party
    preenchidos, do mesmo formato que `calibrar_automatico` produz: uma
    `Regiao` de party window, uma ancora, um `LayoutDaParty` completo,
    `LIMIARES_HP_PADRAO`, `LIMIARES_MP_PADRAO` e `geo`.

    `_semear(alvo, geo)` monta a calibracao de PARTIDA — uma `_nova_party` com
    coordenadas propositalmente diferentes das que a rodada vai gravar — e
    preenche os 27 campos que a party nao possui com valores distinguiveis, mais
    os campos de party do caso 3. Para `assinaturas`, usar
    `l2scanner.identidade.criar_assinatura` sobre um recorte sintetico
    deterministico (`numpy.random.RandomState` com semente fixa, 20x100x3,
    uint8) — medido, isso produz uma assinatura valida com 1299 pixels de texto.
    O ARQUIVO SEMEADO TEM DE PASSAR PELO `Calibracao.carregar`, e nao so
    parecer plausivel. Um arquivo semeado que o `carregar` recusa faz a fusao
    cair no ramo de erro DEPOIS do conserto, e os casos 1 e 2 continuam
    vermelhos com sintoma indistinguivel do defeito original — uma hora de
    depuracao pelo motivo errado. Tres coerencias a respeitar, todas conferidas
    em `l2scanner/calibracao.py`:

    - moldes e ancoras: dicts com `altura`, `largura` e `bytes` em hex cujo
      comprimento CASE com `altura * largura` (`_conferir_o_cabecalho_de_coluna`
      e `mercado_visao.molde_de_hex`);
    - as QUATRO colunas contra a grade (`_conferir_uma_coluna`, linhas 997-1015):
      cada uma exige `dx >= mercado_grade["dx"]` e
      `dx + largura <= mercado_grade["dx"] + mercado_grade["largura"]`. Semear a
      grade primeiro e derivar as quatro colunas de dentro dela, nunca escolher
      numeros soltos;
    - todo `mercado_limiar_*` semeado vive em `(0, 1]` — zero e negativo sao
      recusados por `_numero_de_mercado` e pelas guardas de
      `_conferir_as_chaves_de_mercado`.

    Depois de escrever o auxiliar `_semear`, rodar UMA vez
    `Calibracao.carregar(alvo)` sobre o que ele gravou, antes de escrever
    qualquer caso. Se levantar, o problema esta no semeador e nao no codigo sob
    teste.
    Gravar com `Calibracao.salvar` e devolver o `json.loads` do que ficou no
    disco — e esse dict devolvido que serve de referencia nas assercoes.

    `_dirigir(monkeypatch, alvo, argv, party_nova)` faz os seis monkeypatches
    medidos e chama `l2scanner.calibrar.main()`: `ARQUIVO_CALIBRACAO` apontado
    para `alvo` dentro de `tmp_path`; `capturar_tela` devolvendo um array de
    zeros 400x400x3 com offsets `(0, 0)`; `calibrar_automatico` devolvendo
    `party_nova`; `janela_que_contem` devolvendo `None`;
    `achar_barra_do_proprio` devolvendo `None`; `conferir_visualmente` virando
    no-op, porque ela grava PNG na raiz do repositorio e nada tem a dizer sobre
    a invariante. `sys.argv` vai por `monkeypatch.setattr`.

    O monkeypatch de `ARQUIVO_CALIBRACAO` NAO e detalhe de conveniencia: e a
    unica coisa que mantem o `calibration.json` da maquina do usuario fora do
    alcance desta suite. Escrever isso como comentario no auxiliar, porque quem
    remover a linha achando que e ruido reproduz o incidente dentro do CI.

    Para a geometria, chamar `l2scanner.calibracao.descrever_geometria_da_tela()`
    uma vez e usar o mesmo valor no arquivo semeado e na calibracao nova —
    `carregar` nao confere geometria, mas o teste fica legivel e nao depende da
    tela de quem roda.

    Escrever os cinco casos descritos em `<behavior>`. O caso 1 itera sobre
    `{f.name for f in fields(Calibracao)}` menos a lista de nomes de party
    escrita LITERALMENTE no teste — literal de proposito aqui, para que a
    afirmacao do teste seja independente da constante do codigo de producao; se
    as duas listas divergirem, o caso 4 e quem denuncia.
  </action>

  <precondition>
    O `pytest` roda no Python GLOBAL, e nao no `.venv` (o venv nao tem pytest):
    `python -m pytest --version` responde a partir do interpretador do PATH.
  </precondition>

  <verify>
    <automated>SAIDA=$(python -m pytest tests/test_calibrar_nao_apaga_mercado.py -q 2>&1); RC=$?; echo "$SAIDA" | tail -40; [ $RC -ne 0 ] && echo "$SAIDA" | grep -q "mercado_templates_de_digito" && echo "RED CONFIRMADO"</automated>
  </verify>

  <acceptance_criteria>
    - `tests/test_calibrar_nao_apaga_mercado.py` existe e a rodada acima imprime `RED CONFIRMADO`.
    - `grep -c "def test_" tests/test_calibrar_nao_apaga_mercado.py` devolve pelo menos 5.
    - `grep -c "tmp_path" tests/test_calibrar_nao_apaga_mercado.py` e maior que 0 — o arquivo de trabalho vive em diretorio temporario.
    - O digest do `calibration.json` da raiz e o mesmo antes e depois da rodada: `python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('calibration.json').read_bytes()).hexdigest())"` devolve o mesmo valor NAO-VAZIO nas duas vezes. Digest vazio significa arquivo ausente, e ai a guarda nao guardou nada — isso conta como falha, nao como sucesso.
    - `git status --porcelain calibration.json` nao imprime nada.
  </acceptance_criteria>

  <done>
    O teste esta escrito e VERMELHO, e a falha nomeia o dado de mercado que
    desapareceu — nao um erro de importacao. A saida vermelha esta copiada no
    SUMMARY, que e a prova de que a assercao prende alguma coisa.
  </done>
</task>

<task type="auto">
  <name>Task 2: O seam de fusao — a party grava o que e dela e carrega o resto do disco</name>

  <read_first>
    - `l2scanner/calibrar_mercado.py:2673-2680` — o desenho a espelhar: `arquivo` → `carregar_calibracao(arquivo)` → muta so o que e seu → `cal.salvar(arquivo)`
    - `l2scanner/calibrar.py:894-915` — `calibrar_so_a_propria_barra`, o precedente do MESMO modulo que ja parte da calibracao em disco, com o comentario que explica por que
    - `l2scanner/calibracao.py:145-441` — a lista completa de campos da dataclass, para classificar os 13 donos
    - `l2scanner/calibracao.py:69-71` e `606-627` — `CalibracaoInvalida` e os motivos pelos quais `carregar` levanta
  </read_first>

  <files>l2scanner/calibrar.py</files>

  <action>
    Acrescentar em `l2scanner/calibrar.py`, logo acima de `main()`, uma
    constante e uma funcao.

    `CAMPOS_DA_PARTY` e um `frozenset` com os treze nomes que a calibracao de
    party POSSUI: `party_window`, `ancora`, `layout`, `limiares_hp`,
    `limiares_mp`, `geometria_da_tela`, `hp_proprio`, `nome_proprio`, `nomes`,
    `assinaturas`, `janela`, `party_window_na_janela`, `versao`. O comentario
    dela registra por que a lista e de DONOS e nao de preservados: uma lista de
    preservados exigiria que quem criasse o proximo campo opcional se lembrasse
    de inscreve-lo, e o esquecimento reproduz exatamente o incidente de
    2026-08-30. Assim, o campo novo nasce preservado.

    `fundir_com_a_calibracao_em_disco(nova, caminho)` recebe a `Calibracao`
    recem-deduzida e o caminho do arquivo, e devolve a MESMA `nova` com os
    campos que a party nao possui copiados do que estava gravado. A lista de
    campos a copiar sai por subtracao: `dataclasses.fields(Calibracao)` menos
    `CAMPOS_DA_PARTY`, com `getattr`/`setattr`. Arquivo inexistente e o estado
    legitimo da primeira calibracao da vida: devolve `nova` sem dizer nada.

    Se a leitura falhar — corrompido, versao diferente, arquivo travado,
    assinatura malformada —, NAO propagar. Esta e a rota de recuperacao do
    usuario: se a party parasse de gravar por causa de um arquivo ruim, ele
    ficaria sem saida. Capturar amplo (`except Exception`, com o mesmo
    `# noqa: BLE001` que `calibrar_so_a_propria_barra` ja usa neste modulo),
    imprimir um aviso ALTO comecando pela frase `NAO CONSEGUI PRESERVAR` e
    nomeando o motivo, a calibracao de mercado e as regioes do Tiat como o que
    estava em risco, e seguir com `nova`. Calar aqui seria repetir o defeito
    original com uma camada a mais.

    A docstring da funcao registra o incidente que a justifica: em 2026-08-30 a
    calibracao de party apagou 13 moldes de glifo, 3 ancoras, a grade e um
    limiar do `calibration.json`, porque este caminho era load-mutate-save SEM o
    load; e o lado do mercado ja tinha recebido o mesmo conserto como CR-04.

    No seam: no `main()`, no ponto em que hoje o `cal` recem-deduzido e gravado
    logo antes do bloco que imprime `Calibracao gravada em` e atribui
    `pw = cal.party_window`, reatribuir `cal` ao resultado de
    `fundir_com_a_calibracao_em_disco(cal, ARQUIVO_CALIBRACAO)` antes da
    gravacao. A linha de gravacao em si nao muda.

    NAO tocar nos outros dois pontos de gravacao do modulo: o de
    `calibrar_tiat` e o do ramo `--solo` ja partem de
    `Calibracao.carregar(ARQUIVO_CALIBRACAO)` e ja preservam. Acrescentar, no
    comentario da constante, a frase que diz isso, para que a proxima leitura
    nao os "conserte" tambem.

    Restricoes desta task: `VERSAO_DO_ESQUEMA` fica em 2; nenhuma dependencia
    nova entra; nenhum valor que a party grava hoje muda; `l2scanner/rastreador.py`
    e o portao de brilho de `l2scanner/visao.py` nao sao tocados. `dataclasses`
    ja e importado no modulo para o `@dataclass` de `BarraEncontrada` — conferir
    se `fields` precisa entrar no import existente.
  </action>

  <verify>
    <automated>python -m pytest tests/test_calibrar_nao_apaga_mercado.py -q</automated>
  </verify>

  <acceptance_criteria>
    - Os cinco casos da Task 1 passam.
    - `grep -c "CAMPOS_DA_PARTY" l2scanner/calibrar.py` e maior ou igual a 2 (a definicao e o uso).
    - `grep -c "fundir_com_a_calibracao_em_disco" l2scanner/calibrar.py` e igual a 2 (a definicao e a unica chamada).
    - `grep -cE '^ +cal\.salvar\(ARQUIVO_CALIBRACAO\)$' l2scanner/calibrar.py` continua em 3 — os tres pontos de gravacao seguem existindo e nenhum foi duplicado ou removido.
    - `git diff -U0 l2scanner/calibrar.py | grep -c "VERSAO_DO_ESQUEMA"` devolve 0 — nenhum bump.
    - `git diff --name-only` nao lista `l2scanner/rastreador.py` nem `l2scanner/visao.py`.
    - `python -c "import l2scanner.calibrar as c; from dataclasses import fields; from l2scanner.calibracao import Calibracao; n={f.name for f in fields(Calibracao)}; assert c.CAMPOS_DA_PARTY <= n; assert not any(x.startswith('mercado_') for x in c.CAMPOS_DA_PARTY); print('OK', len(n - c.CAMPOS_DA_PARTY), 'campos preservados')"` imprime `OK 27 campos preservados`.
  </acceptance_criteria>

  <done>
    Rodar a calibracao de party sobre um `calibration.json` com dados de mercado
    deixa os 27 campos nao-party identicos, e os 13 campos da party recebem o
    valor novo — inclusive voltando a vazio/`None` quando a rodada nao produziu
    valor. Um arquivo ilegivel nao impede a gravacao e produz o aviso alto.
  </done>

  <reversibility rating="reversible">
    Codigo mais teste, sem migracao de dados e sem mudanca de esquema; `git revert` desfaz por inteiro.
  </reversibility>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Prender tambem o `--solo`, e a suite inteira verde com o arquivo real intocado</name>

  <read_first>
    - `l2scanner/calibrar.py:826-915` — `calibrar_so_a_propria_barra`: quais funcoes ela chama antes de `Calibracao.carregar` (`listar_janelas_do_jogo`, `achar_janela`, `origem_da_janela`, `JanelaSource`, `achar_barra_do_proprio`)
    - `l2scanner/calibrar.py:1103-1130` — o ramo `--solo` de `main()` ate o seu `cal.salvar`
    - O arquivo `tests/test_calibrar_nao_apaga_mercado.py` escrito na Task 1, para reaproveitar `_semear` e o monkeypatch de `ARQUIVO_CALIBRACAO`
  </read_first>

  <files>tests/test_calibrar_nao_apaga_mercado.py</files>

  <behavior>
    - Caso 6 — `--solo` preserva: semear o mesmo arquivo com os 27 campos
      preenchidos, dirigir `main()` com `--solo` e uma janela falsa, e exigir
      que os 27 continuem identicos. `--solo` ja preservava antes desta rodada;
      o caso existe para que ele NAO deixe de preservar numa refatoracao futura
      — que e exatamente como o lado da party ficou aberto depois do CR-04.
    - O caso deve passar TAMBEM se rodado contra o codigo anterior a Task 2.
      Isso nao o torna inutil: ele nao prova o conserto, prova a invariante. Se
      passar por acidente e nao por desenho, o SUMMARY diz isso com todas as
      letras.
  </behavior>

  <action>
    Acrescentar o caso 6 ao arquivo da Task 1.

    Monkeypatchar, no modulo `l2scanner.calibrar`: `listar_janelas_do_jogo`
    devolvendo uma lista com um titulo unico no formato `Personagem - XM
    Essence`; `achar_janela` devolvendo um inteiro qualquer; `origem_da_janela`
    devolvendo `(0, 0)`; `JanelaSource` por uma classe falsa cujo construtor
    aceita os dois argumentos, cujo `capturar_completo` devolve um array de
    zeros e cujo `fechar` nao faz nada; `achar_barra_do_proprio` devolvendo uma
    `Regiao` valida; `_conferencia_do_solo` virando no-op, para nao gravar PNG
    na raiz. `ARQUIVO_CALIBRACAO` continua apontado para `tmp_path`, pelo mesmo
    motivo de sempre.

    Afirmar os 27 campos identicos, e afirmar tambem o que o modo solo
    LEGITIMAMENTE muda: `janela`, `hp_proprio` e `nome_proprio`. A party window
    do arquivo semeado tem de sobreviver — e o que o `.bat` do modo solo promete
    ao usuario por escrito.

    Depois, rodar a suite completa e reconciliar com o baseline. O baseline
    verde e 1824 passed, 2 skipped; a rodada nova tem de ser esse numero mais os
    casos novos deste arquivo, sem nenhum teste que passava passando a falhar.
    `tests/test_agenda.py` tem um flake conhecido que aborta a sessao inteira
    com `KeyboardInterrupt` perto de ~88 testes: abortar NAO e falhar — rodar de
    novo. Se abortar tres vezes seguidas, registrar no SUMMARY em vez de tratar
    como falha.

    Antes e depois da suite completa, calcular o digest SHA-256 do
    `calibration.json` da raiz e conferir que e o mesmo. Ele e gitignored,
    carrega os 13 moldes do usuario, e nenhuma linha desta rodada tem permissao
    de toca-lo.
  </action>

  <verify>
    <automated>D() { python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('calibration.json').read_bytes()).hexdigest())" 2>/dev/null; }; ANTES=$(D); [ -n "$ANTES" ] || { echo "SEM DIGEST INICIAL: calibration.json ausente ou ilegivel — o portao seria VACUO, e guarda vacua da confianca falsa"; exit 1; }; python -m pytest -q; RC=$?; DEPOIS=$(D); [ -n "$DEPOIS" ] || { echo "O ARQUIVO REAL SUMIU DURANTE A SUITE"; exit 1; }; [ "$ANTES" = "$DEPOIS" ] || { echo "O ARQUIVO REAL FOI ALTERADO"; exit 1; }; echo "CALIBRATION.JSON INTOCADO"; exit $RC</automated>
  </verify>

  <acceptance_criteria>
    - A suite completa termina verde, com contagem igual ao baseline (1824 passed, 2 skipped) mais os casos novos deste arquivo, e nenhuma falha nova.
    - A rodada imprime `CALIBRATION.JSON INTOCADO`.
    - `git status --porcelain calibration.json` nao imprime nada.
    - `grep -c "def test_" tests/test_calibrar_nao_apaga_mercado.py` devolve pelo menos 6.
    - `python -m pytest tests/test_firewall_escopo.py -q` passa — nenhuma biblioteca de sintese de input entrou na arvore.
  </acceptance_criteria>

  <done>
    Os quatro caminhos de gravacao estao classificados e, dos tres alcancaveis
    por teste, os tres estao presos: `--auto` e `--selecionar` pelo caso 1 e 2,
    `--solo` pelo caso 6. O `--tiat` esta documentado como nao alcancavel, com o
    motivo, na docstring do modulo de teste. A suite inteira esta verde e o
    `calibration.json` real tem o mesmo digest com que a rodada comecou.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| suite de testes → `calibration.json` da raiz | Um teste que escreva no arquivo real destroi estado de maquina insubstituivel (13 moldes de glifo, cada um um arrasto de mouse mais um rotulo digitado). O arquivo e gitignored: nao ha `git checkout` que o traga de volta. |
| `calibration.json` em disco → `Calibracao.carregar` | Entrada nao confiavel: editada a mao, possivelmente corrompida ou de outra versao. Agora tambem lida DENTRO do caminho de gravacao da party. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-apd-01 | Tampering | `tests/test_calibrar_nao_apaga_mercado.py` escrevendo no `calibration.json` real | high | mitigate | `monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", tmp_path / ...)` em todo caso; gate de digest SHA-256 antes/depois da suite na Task 3; `git status --porcelain calibration.json` vazio como criterio de aceitacao nas Tasks 1 e 3 |
| T-apd-02 | Denial of Service | `fundir_com_a_calibracao_em_disco` propagando excecao de leitura | high | mitigate | Captura ampla com aviso alto (`NAO CONSEGUI PRESERVAR`) e prosseguimento; a party continua conseguindo gravar sobre um arquivo ruim, que e a rota de recuperacao do usuario |
| T-apd-03 | Information Disclosure | Dado de mercado silenciosamente destruido (o incidente) | high | mitigate | Lista de DONOS por subtracao de `dataclasses.fields`, mais os casos 1, 2 e 6 do teste afirmando os 27 campos byte a byte |
| T-apd-04 | Tampering | Campo opcional criado no futuro entrar no lado errado da classificacao | medium | mitigate | O default e PRESERVAR (subtracao, nao lista de inclusao); caso 4 afirma por prefixo que nenhum `mercado_*` esta entre os donos |
| T-apd-05 | Elevation of Privilege | Instalacao de pacote no fluxo | low | accept | Nenhuma task instala nada: zero `npm`/`pip`/`cargo` install no plano, nenhuma dependencia nova. `tests/test_firewall_escopo.py` (FIRE-01) roda na suite completa e e criterio de aceitacao da Task 3. |
</threat_model>

<verification>
- Os cinco casos da Task 1 estavam VERMELHOS antes da Task 2 e ficam verdes depois; a saida vermelha esta no SUMMARY.
- A suite completa fecha no baseline mais os casos novos, sem falha nova. Aborto por `KeyboardInterrupt` em `tests/test_agenda.py` nao conta como falha — rodar de novo.
- `calibration.json` da raiz com o mesmo digest SHA-256 do inicio ao fim, e `git status --porcelain calibration.json` vazio.
- `git diff --name-only` lista apenas `l2scanner/calibrar.py` e `tests/test_calibrar_nao_apaga_mercado.py`.
- `VERSAO_DO_ESQUEMA` continua em 2.

<human-check>
Uma conferencia que o teste nao substitui, porque so a maquina do usuario tem os
13 moldes de verdade: com o conserto no lugar, COPIAR o `calibration.json` real
para um nome de rascunho, rodar `python -m l2scanner.calibrar --auto` apontado
para essa copia (ou aceitar rodar o `calibrar.bat` normal ja tendo a copia de
seguranca ao lado), e confirmar que `mercado_templates_de_digito` continua com
13 entradas depois da rodada. A copia de seguranca vem PRIMEIRO — o plano ja
custou os moldes uma vez.
</human-check>

Fechar a JANELA 13 na `STATE.md` do workstream mercado depois que a verificacao
passar, citando o commit.
</verification>

<success_criteria>
- Existe um teste que falhava no codigo de 2026-08-30 pela ausencia do dado de mercado e passa depois do conserto, e a saida vermelha esta registrada.
- Os 27 campos que a calibracao de party nao possui sobrevivem a `--auto`, a `--selecionar` e a `--solo`.
- Os 13 campos que ela possui continuam recebendo exatamente o valor que ela grava hoje.
- Os dois pontos de gravacao que ja estavam corretos (`calibrar_tiat` e o ramo `--solo`) nao foram alterados.
- O `calibration.json` real nunca foi tocado, por nenhuma linha do plano.
- Nenhuma dependencia nova; `VERSAO_DO_ESQUEMA` intacta; `rastreador.py` e o portao de brilho de `visao.py` intactos.
</success_criteria>

<output>
Create `.planning/workstreams/mercado/quick/260830-apd-party-calibration-nao-pode-apagar-a-cali/260830-apd-SUMMARY.md` when done.
</output>
