---
phase: quick-260902-syn
plan: 01
type: execute
wave: 1
quick_id: 260902-syn
base_commit: 77531ce
depends_on: []
files_modified:
  - tools/medir_leitura_de_glifo.py
  - tests/test_medir_leitura_de_glifo.py
autonomous: true
requirements: [QUICK-260902-syn]

estimate:
  tokens: 62000
  raw_tokens: 62000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Um rotulo com taxa de recusa alta ENCABECA a ordem mesmo com n pequeno, diante de um rotulo saudavel de n grande."
    - "Um rotulo com UM score catastrofico isolado NAO encabeca a ordem — o pior score sozinho nao decide a fragilidade."
    - "O relatorio imprime, por rotulo: n, os quantis de score, os quantis de margem, e as duas contagens abaixo das duas travas."
    - "Sem `--por-rotulo` a ferramenta faz exatamente o que fazia — o padrao da chave e falso."
    - "Com o piso ou a margem ausentes da calibracao o relatorio DIZ que estao ausentes e nao substitui por numero proprio."
    - "`9` x `4`, medido agora na mecanica de producao, fica abaixo de `0` x `8`."
    - "A ordem impressa e a mesma em duas execucoes sobre a mesma populacao."
    - "Nenhum arquivo sob `l2scanner/` muda."
  artifacts:
    - "tools/medir_leitura_de_glifo.py::fragilidade_por_rotulo"
    - "tools/medir_leitura_de_glifo.py::imprimir_a_fragilidade_por_rotulo"
    - "tools/medir_leitura_de_glifo.py::casamento_entre_moldes"
    - "tests/test_medir_leitura_de_glifo.py::TestAFragilidadePorRotulo"
    - "tests/test_medir_leitura_de_glifo.py::TestOsMoldesQueNaoSeParecem"
  key_links:
    - "varrer -> ResultadoDaVarredura.amostras -> fragilidade_por_rotulo -> imprimir_a_fragilidade_por_rotulo"
    - "Calibracao.mercado_limiar_de_leitura_de_glifo / mercado_margem_de_leitura_de_glifo -> as duas contagens de recusa do relatorio"
    - "glifos_de_calibracao(cal) -> casamento_entre_moldes -> a linha impressa `9` x `4` contra `0` x `8`"
---

<objective>
Dois erros de leitura em campo hoje (2026-09-02), e nos dois um `9` virou `4`: quantidade
9 lida como 4 (`Improved Scroll: Enchant C-grade Armor`, residuo 1948) e incremento 5999
lido como 5949 (`total=11999 incremento=5949 n=2 residuo=101`). O segundo esta PROVADO sem
a tela: o jogo deriva o incremento do total, entao `59,49 x 2 = 118,98` nunca poderia estar
ao lado de `119,99` na mesma linha. A guarda de Adena recusou — o dado ruim nao entrou no
CSV.

Esta task NAO conserta nada. Ela faz `tools/medir_leitura_de_glifo.py`, que ja varre as 8
gravacoes do censo COM A GEOMETRIA DE PRODUCAO, quebrar a distribuicao que ele ja imprime
POR ROTULO — para o `9` ser acusado ou inocentado por numero em vez de por palpite. E
grava no fonte as duas hipoteses que a medicao ja REFUTOU, mais o arnes que foi jogado
fora, para ninguem repetir os tres.

Purpose: a ferramenta hoje diz `p1=0,1918` sobre 2.057 glifos e nao diz de QUEM e esse
p1. Um relatorio agregado nunca aponta um culpado; ele so informa que existe um.

Output: um relatorio por rotulo ordenado por fragilidade, atras de uma chave de linha de
comando; a distancia `9`x`4` medida na hora; e tres refutacoes escritas no fonte.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.claude/CLAUDE.md
@tools/medir_leitura_de_glifo.py
@tests/test_medir_leitura_de_glifo.py
</context>

<restricoes_inegociaveis>
Valem para as DUAS tasks. Violar qualquer uma invalida o plano inteiro.

DIAGNOSTICO, NAO CONSERTO — o criterio de escopo:

- NAO tocar em NENHUM molde, em nenhuma circunstancia.
- NAO tocar em `mercado_limiar_de_leitura_de_glifo` (0.4698) nem em
  `mercado_margem_de_leitura_de_glifo` (0.0370). O relatorio os LE; ele nunca os propoe,
  nunca os grava, nunca os discute.
- NAO ligar `mercado_tolerancia_do_cruzamento` — continua `None`.
- NAO rodar a ferramenta com `--gravar`. Nunca, nem "so para ver".
- NENHUM arquivo sob `l2scanner/` muda. Este plano escreve em `tools/` e em `tests/` e em
  mais lugar nenhum. Um plano que conserta alguma coisa leu o proprio escopo errado.

O RESTO DA CASA:

- NUNCA commitar `calibration.json` — gitignored, estado de maquina, 13+13 moldes
  cortados a mao.
- NUNCA escrever em `.mercado/` — dado de producao do usuario, e o vigia esta RODANDO
  neste momento. Nao matar, nao reiniciar. Todo teste usa `tmp_path`.
- `recordings/` e somente leitura e NUNCA por glob amplo: `pre-voo` sozinha tem 1502 PNGs
  e varreduras assim ja mataram agente por limite de taxa. A varredura da propria
  ferramenta, sobre as 8 gravacoes NOMEADAS, e a logica limitada dela e pode rodar.
- NENHUMA dependencia nova, e JAMAIS uma biblioteca de sintese de input (pyautogui,
  pydirectinput, pynput, keyboard, mouse).
- NAO tocar em `l2scanner/rastreador.py` nem no portao da propria barra em
  `l2scanner/visao.py` (ja coberto pela regra acima, repetido de proposito).
- NAO tocar nos arquivos do agente paralelo: `respawn.py`, `bosses.py`, `agenda.py`,
  `sessao.py`, `test_bosses.py`, `identidade.py`, `discord/`, `dashboard.py`, `renda*`.
- NUNCA `git commit --amend`, NUNCA `git stash`. NAO mexer em `VERSAO_DO_ESQUEMA` (2).
- Comentarios e mensagens de commit em portugues, na voz do modulo vizinho.
- O portao de LAYOUT que entrou no 260902-ca4 continua sendo chamado da PRODUCAO
  (`LeitorDePagina`) e nunca reimplementado aqui. Este plano nao encosta nele.
- A suite ABORTA em `tests/test_agenda.py` (KeyboardInterrupt deliberado, pre-existente,
  area de outro agente). Rodar SEMPRE
  `python -m pytest -q --ignore=tests/test_agenda.py`.
- MEDIR A BASE PRIMEIRO, antes de escrever uma linha, e anotar o numero. No momento do
  planejamento, em `77531ce`, ela era **5260 passed, 61 skipped em 259s**. O branch e
  compartilhado e outros agentes seguem mesclando, entao esse numero e referencia e NAO
  gabarito: vale o que a medicao do inicio da task devolver. Se vier ABAIXO de 5260,
  parar e relatar — alguem perdeu teste no caminho.
- PYTEST RODA NO PYTHON GLOBAL (`python -m pytest`). A FERRAMENTA roda no
  `.venv/Scripts/python.exe`. Os dois interpretadores nao sao intercambiaveis neste
  repositorio.
</restricoes_inegociaveis>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: A fragilidade POR ROTULO — quem esta em apuros se nomeia sozinho</name>

  <files>
tools/medir_leitura_de_glifo.py,
tests/test_medir_leitura_de_glifo.py
  </files>

  <read_first>
- `tools/medir_leitura_de_glifo.py:1-64` — a docstring do modulo inteira. Ela ja carrega a
  distribuicao AGREGADA (`score: min=0,0818 p1=0,1918 p5=0,7242 mediana=1,0000`) e a razao
  pela qual o piso de LEITURA nao e o limiar de COLISAO. E a voz a imitar.
- `tools/medir_leitura_de_glifo.py:434:449` — `Amostra`, que ja carrega
  `gravacao/arquivo/linha/coluna/rotulo/score/margem`. Ela nao muda.
- `tools/medir_leitura_de_glifo.py:733:742` — `_quantis`, que ja formata
  `n / min / p1 / p5 / mediana / max`. E a casa unica desse formato e sera REUSADA.
- `tools/medir_leitura_de_glifo.py:859:934` — o RELATORIO 1 como esta hoje, incluindo o
  bloco `O PIOR POR ROTULO` (pior score, pior margem, mediana) e o bloco do par `0` x `8`.
  O relatorio novo entra DEPOIS do bloco do par `0` x `8` e nao apaga nenhum dos dois.
- `tools/medir_leitura_de_glifo.py:767:777` — o `ArgumentParser` de `main`, onde a chave
  nova entra ao lado de `--gravar`.
- `l2scanner/mercado_leitura.py:648:690` — `pontuar_glifos`, que devolve
  `(rotulo, score, margem_sobre_o_segundo)` SEM piso, e a docstring que explica por que o
  corte nao mora la. Ler para entender de onde vem cada numero; NAO editar.
- `l2scanner/calibracao.py:463:464` — os dois campos que o relatorio le,
  `mercado_limiar_de_leitura_de_glifo` e `mercado_margem_de_leitura_de_glifo`.
- `tests/test_medir_leitura_de_glifo.py:1:40` — a docstring do teste, que explica por que
  nada aqui depende de `recordings/` nem de `calibration.json`.
- `tests/test_medir_leitura_de_glifo.py:60:83` — `_carregar_a_ferramenta` e os simbolos ja
  re-exportados como `ferramenta.X`. Os simbolos novos entram nessa mesma convencao.
- `tests/test_medir_leitura_de_glifo.py:417:540` — `TestOPortaoDeLayoutDaPRODUCAO_E_CHAMADO`
  inteira, com o CONTROLE NEGATIVO. E o molde de rigor a seguir: a docstring da classe diz
  QUAL propriedade esta sendo medida e por que o controle separa duas afirmacoes.
  </read_first>

  <behavior>
A funcao `fragilidade_por_rotulo(amostras, piso, margem_minima)` e PURA: recebe a lista de
`Amostra` que `varrer` ja produziu e devolve uma lista ORDENADA de dicionarios, um por
rotulo. Ela nao varre, nao le arquivo, nao imprime.

Cada dicionario carrega, no minimo:

    rotulo, n,
    score_min, score_p1, score_p5, score_mediana,
    margem_min, margem_p1, margem_p5, margem_mediana,
    abaixo_do_piso, abaixo_da_margem, taxa_de_recusa

`abaixo_do_piso` conta `score < piso`. `abaixo_da_margem` conta `margem < margem_minima`.
`taxa_de_recusa` e a UNIAO dos dois conjuntos dividida por `n` — a amostra que cai nas
duas travas conta UMA vez, porque a producao a recusaria uma vez.

A ORDEM e por `taxa_de_recusa` DECRESCENTE, com desempate por `score_p1` crescente, depois
`margem_p1` crescente, depois `rotulo` crescente.

Testes (classe `TestAFragilidadePorRotulo`), todos sobre populacao SINTETICA de `Amostra`
montada a mao, com a forma por rotulo CONHECIDA por construcao:

  - Teste 1 — o rotulo deliberadamente fraco ENCABECA. Populacao: `'7'` com 10 amostras,
    6 delas com score abaixo do piso; `'4'` com 10, 2 delas abaixo da margem; `'1'` com
    10 limpas. Afirmar `fragilidade_por_rotulo(...)[0]["rotulo"] == "7"` e que a ordem
    completa e `["7", "4", "1"]`.
  - Teste 2 — os NUMEROS do rotulo fraco sao os construidos. Sobre a mesma populacao,
    afirmar `n == 10`, `abaixo_do_piso == 6`, `abaixo_da_margem` e `taxa_de_recusa == 0.6`
    exatos, e os quatro quantis de score e os quatro de margem contra os valores
    calculados no proprio teste com `numpy` sobre a lista construida. Nao afirmar "existe
    a chave"; afirmar o VALOR.
  - Teste 3 — o relatorio IMPRIME a ordem e os numeros. Com `capsys`, chamar
    `imprimir_a_fragilidade_por_rotulo(...)` e afirmar que
    `saida.index("'7'") < saida.index("'4'") < saida.index("'1'")` e que a linha do `'7'`
    carrega o `n=10` e as duas contagens. A ordem impressa e a mesma que a funcao devolve.
  - Teste 4 — n PEQUENO com recusa alta ganha de n GRANDE saudavel. `'A'` com 4 amostras,
    3 recusadas (0,75); `'B'` com 400 amostras, 20 recusadas (0,05). Afirmar que `'A'`
    vem antes. Isto prende a normalizacao por `n`: uma chave por CONTAGEM enterraria um
    rotulo raro e fragil debaixo de um comum e sadio, e a virgula e o `9` sao justamente
    os candidatos a raro.
  - Teste 5 — CONTROLE DE CHAVE: o pior score ISOLADO nao decide. `'A'` com 100 amostras,
    99 limpas e 1 com score 0,01 (taxa 0,01); `'B'` com 10 amostras, 3 abaixo da margem
    (taxa 0,30). Afirmar que `'B'` vem antes de `'A'` MESMO tendo `'A'` o pior
    `score_min` de longe. Isto prende a chave escolhida contra a chave rejeitada.
  - Teste 6 — a funcao nao altera a populacao de entrada (comparar a lista antes e depois).
  - Teste 7 — a ordem e ESTAVEL: duas chamadas sobre a mesma populacao devolvem a mesma
    sequencia de rotulos, e uma populacao embaralhada devolve a mesma sequencia. Um
    relatorio cuja ordem se mexe nao pode ser comparado entre duas execucoes.
  - Teste 8 — piso ou margem AUSENTES: com `piso=None` ou `margem_minima=None`, a funcao
    devolve as linhas com os quantis e com as contagens em `None` (nao em zero), e o
    impresso DIZ que a trava esta ausente. Zero e uma medicao; ausente nao e zero.
  - Teste 9 — o padrao da chave de linha de comando e FALSO:
    `construir_analisador().parse_args([]).por_rotulo is False`, e com a chave passada e
    verdadeiro. E o que prende "a ferramenta continua fazendo o que fazia quando o
    relatorio novo nao e pedido".
  </behavior>

  <action>
Escrever a funcao pura, o impressor, a chave de linha de comando, e os nove testes.

1. `fragilidade_por_rotulo(amostras, piso, margem_minima) -> list[dict]` em
   `tools/medir_leitura_de_glifo.py`, junto do resto do bloco de relatorio (logo depois de
   `_quantis`). Pura: sem leitura de arquivo, sem impressao, sem varredura.

2. A DOCSTRING DELA CARREGA A ESCOLHA DA CHAVE DE FRAGILIDADE E A RAZAO. Esta prosa e
   metade do valor da task; escrever com o mesmo cuidado do codigo. Ela precisa dizer, com
   estas cinco justificativas:

   - A chave esta nas MESMAS unidades da decisao. As duas travas sao o que a producao usa
     para recusar um glifo; ordenar por quantas vezes um rotulo as encosta poe no topo o
     rotulo que a producao mais recusa. Qualquer outra chave mede coisa que a decisao nao
     consulta.
   - Ela e normalizada por `n`. Uma chave por contagem enterraria um rotulo raro e fragil
     debaixo de um comum e sadio, e coroaria um comum so pelo volume.
   - O PIOR SCORE SOZINHO FOI REJEITADO: um unico recorte ocluido ou meio rolado coroaria
     um rotulo saudavel. Chave de amostra unica e amplificador de ruido, e este relatorio
     existe para ser acreditado sem segunda fonte.
   - A MEDIANA FOI REJEITADA: ela esconde a cauda, e o `8` e a prova — mediana 0,7242
     contra o proprio molde e a producao lendo bem. Uma chave que elege o `8` como o mais
     doente em toda execucao e uma chave que ninguem le duas vezes.
   - O desempate e deterministico para a ordem nao se mexer entre execucoes: relatorio
     cuja ordem anda nao pode ser comparado com o da semana passada.

3. NA MESMA DOCSTRING, A RESSALVA QUE DECIDE SE O `9` E ACUSADO OU INOCENTADO — e a parte
   que impede a leitura errada do proprio relatorio:

   - Os baldes sao pelo rotulo que a ferramenta PROPOS, nunca pela verdade: a varredura
     nao tem gabarito. Um `9` lido como `4` cai no balde do `4` e nunca aparece no do `9`.
   - INOCENTA POR AUSENCIA: se o balde do `9` tiver taxa de recusa baixa e margens
     fundas, o erro de campo nao veio do score do `9` estar fraco, e a busca se move para
     a segmentacao (`segmentar_glifos`) e para a geometria da coluna.
   - ACUSA POR CAUDA: se o balde do `4` carregar uma cauda de margem baixa, e nessa cauda
     que um glifo estrangeiro estaria sentado — e cada `Amostra` guarda
     `(gravacao, arquivo, linha, coluna)`, entao a cauda pode ser reconferida frame a
     frame.

4. `imprimir_a_fragilidade_por_rotulo(amostras, piso, margem_minima)` — chama a funcao
   pura e imprime. REUSAR `_quantis` para as duas linhas de estatistica: o formato
   `n/min/p1/p5/mediana/max` ja tem uma casa so, e uma segunda copia dele seria a porta
   pela qual os dois relatorios passariam a formatar diferente o mesmo numero. O cabecalho
   de cada rotulo leva o rotulo, o `n`, as duas contagens e a taxa.

5. Os DOIS numeros de trava vem de `cal.mercado_limiar_de_leitura_de_glifo` e
   `cal.mercado_margem_de_leitura_de_glifo` — os CONFIGURADOS, lidos da calibracao. Nunca
   escritos no fonte, e nunca o par PROPOSTO que o RELATORIO 1 calcula: o par proposto e
   uma hipotese, e a pergunta aqui e sobre a trava que esta valendo. Se um deles for
   `None`, imprimir que esta AUSENTE e seguir com os quantis. Um relatorio que inventasse
   a propria trava mediria um limiar que ninguem usa.

6. Extrair a construcao do `ArgumentParser` de `main` para `construir_analisador()`, e
   `main` passa a chama-la. Extracao de mesma semantica, sem mudar nenhum texto de ajuda,
   nenhum nome de chave e nenhum padrao. Acrescentar
   `--por-rotulo`, `action="store_true"`, ao lado de `--gravar`.

7. Chamar o impressor em `main` SO sob `if opcoes.por_rotulo:`, logo depois do bloco do par
   `0` x `8` do RELATORIO 1 — mesma populacao, mesmos numeros, quebrados. O bloco e
   ADITIVO: sem a chave, nada a mais e impresso e nada a menos.

8. Os testes vao para `tests/test_medir_leitura_de_glifo.py`, na classe
   `TestAFragilidadePorRotulo`, com docstring de classe dizendo QUAL propriedade a classe
   mede e por que os Testes 4 e 5 sao controles de chave e nao repeticao do Teste 1.
   Re-exportar os simbolos novos no topo do arquivo, na convencao ja existente
   (`ferramenta.X`). Montar as amostras com `ferramenta.Amostra`, populacao a mao, nunca
   varrendo gravacao — esta task nao precisa de pixel nenhum.
  </action>

  <verify>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_medir_leitura_de_glifo.py -v -k "TestAFragilidadePorRotulo"
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_medir_leitura_de_glifo.py
    </automated>
    <automated>
python -c "import importlib.util,sys,pathlib; p=pathlib.Path('tools/medir_leitura_de_glifo.py'); s=importlib.util.spec_from_file_location('m',p); m=importlib.util.module_from_spec(s); sys.modules['m']=m; s.loader.exec_module(m); o=m.construir_analisador().parse_args([]); assert o.por_rotulo is False; assert o.gravar is False; o2=m.construir_analisador().parse_args(['--por-rotulo']); assert o2.por_rotulo is True and o2.gravar is False; print('padrao da chave OK')"
    </automated>
    <automated>
git diff --name-only HEAD | python -c "import sys; mudados=sorted(l.strip() for l in sys.stdin if l.strip()); assert mudados==['tests/test_medir_leitura_de_glifo.py','tools/medir_leitura_de_glifo.py'], mudados; print('so a ferramenta e o teste dela:', mudados)"
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py
    </automated>
  </verify>

  <prova_por_mutacao>
OBRIGATORIA e nao opcional. Depois de a task estar VERDE:

1. Em `fragilidade_por_rotulo`, inverter o sentido da ordenacao pela taxa de recusa
   (decrescente para crescente) — uma linha, na producao da funcao, nunca no teste.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestAFragilidadePorRotulo" -v`.
3. Confirmar VERMELHO nos Testes 1, 3, 4 e 5. Se algum deles ficar VERDE com a ordem
   invertida, esse teste nao esta medindo ordem nenhuma e tem de ser reescrito antes de
   seguir.
4. COPIAR A LINHA DE RESUMO DO PYTEST VERBATIM para o corpo do commit.
5. Reverter a mutacao e reconfirmar o verde.
  </prova_por_mutacao>

  <mutacao_de_CONTROLE>
OBRIGATORIA, e ela tem de ficar VERDE. Prende o criterio ao COMPORTAMENTO em vez de a
forma do codigo — foi o que pegou um problema real no 260902-pqf e virou pratica da casa.

1. Refatorar `fragilidade_por_rotulo` sem mudar a semantica: trocar a construcao da linha
   por rotulo por um laco explicito equivalente (ou o contrario, se ja for laco), e
   calcular a uniao das duas recusas por conjunto de indices em vez de por soma com
   subtracao da intersecao — mesmos numeros, mesma ordem, escrita diferente.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestAFragilidadePorRotulo" -v`.
3. Confirmar VERDE. Se cair, o teste esta preso ao formato do codigo e nao ao numero — e
   e o TESTE que tem de ser reescrito, jamais a mutacao que tem de ser desfeita para
   "passar".
4. COPIAR A LINHA DE RESUMO VERBATIM para o corpo do commit, ao lado da mutacao de cima.
5. Reverter e reconfirmar o verde.
  </mutacao_de_CONTROLE>

  <done>
- `fragilidade_por_rotulo` e `imprimir_a_fragilidade_por_rotulo` existem, a primeira pura,
  e os nove testes da classe passam.
- A docstring da funcao carrega as cinco justificativas da chave (as duas rejeicoes
  nomeadas: pior score isolado e mediana) e a ressalva do balde por rotulo PROPOSTO, com
  os dois sentidos escritos — inocenta por ausencia, acusa por cauda.
- `construir_analisador().parse_args([]).por_rotulo` e `False` e `.gravar` e `False`.
- As duas travas vem da calibracao; `None` e relatado como AUSENTE e nao como zero.
- `git diff --name-only HEAD` lista exatamente os dois caminhos desta task — nada sob
  `l2scanner/`, nada de estado de maquina.
- As duas mutacoes rodadas, com os dois resumos de pytest copiados verbatim no commit.
- Suite completa na base medida no inicio da task, ou acima dela pelos testes novos.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: As tres refutacoes, e a distancia `9` x `4` medida na hora</name>

  <files>
tools/medir_leitura_de_glifo.py,
tests/test_medir_leitura_de_glifo.py
  </files>

  <read_first>
- `tools/medir_leitura_de_glifo.py:1:64` — de novo a docstring do modulo, agora para
  ESCREVER nela. As tres refutacoes entram como uma secao nova, na voz das duas que ja
  estao la (`O PISO DE LEITURA NAO E ...`, `A GUARDA DE CRUZAMENTO E DECIDIVEL ...`).
- `tools/medir_leitura_de_glifo.py:88:122` — o bloco de imports de `l2scanner`, e o
  comentario que explica por que a seta aponta producao -> ferramenta. `casamento_da_ancora`
  e `_alinhar_por_preenchimento` entram por ali.
- `l2scanner/mercado_leitura.py:479` — `_alinhar_por_preenchimento`, a assinatura e o que
  ela devolve.
- `l2scanner/mercado_visao.py:102` — `casamento_da_ancora`, a assinatura.
- `l2scanner/mercado_leitura.py:670:680` — como `pontuar_glifos` compoe as duas. E a
  composicao a espelhar, e nunca a reescrever de outro jeito.
- `tests/test_medir_leitura_de_glifo.py:133:146` — a fixtura `moldes`, que recorta os 11
  glifos de um caractere das PROPRIAS fixturas versionadas. Ela ja contem `9`, `4`, `0` e
  `8` (`18,90` da o `9`, `2,45` e `48` dao o `4`). E a unica fonte de molde que existe em
  clone limpo.
  </read_first>

  <behavior>
`casamento_entre_moldes(moldes, a, b) -> float` alinha os dois moldes com
`_alinhar_por_preenchimento` e pontua com `casamento_da_ancora` — a MESMA composicao de
`pontuar_glifos`, importada e nunca reescrita.

Testes (classe `TestOsMoldesQueNaoSeParecem`), sobre a fixtura `moldes`:

  - Teste 1 — REFUTACAO MEDIDA: `casamento_entre_moldes(moldes, "9", "4")` fica
    materialmente ABAIXO de `casamento_entre_moldes(moldes, "0", "8")`. Os dois numeros
    medidos nas fixturas vao ESCRITOS VERBATIM na docstring do teste, com a data. Se a
    ordem NAO se sustentar sobre os moldes de fixtura, PARAR e RELATAR o numero: a
    afirmacao seria falsa e a refutacao teria de ser reescrita. Jamais afrouxar a
    afirmacao para caber no que saiu.
  - Teste 2 — a funcao E a composicao de PRODUCAO, provado por VALOR e nao por inspecao:
    para um par amostrado, o teste calcula
    `casamento_da_ancora(*_alinhar_por_preenchimento(moldes[a], moldes[b]))` com os
    simbolos importados da producao e afirma igualdade exata com
    `casamento_entre_moldes`. Se a ferramenta trocar de mecanica, este teste cai.
  - Teste 3 — ancora de sanidade: um molde contra si mesmo da 1,0 (com a tolerancia de
    ponto flutuante da casa). Sem ela, uma mutacao que devolvesse lixo poderia passar
    despercebida no Teste 1.
  </behavior>

  <action>
1. `casamento_entre_moldes(moldes, a, b)` em `tools/medir_leitura_de_glifo.py`, tres
   linhas, compondo os dois simbolos de producao. Importar
   `_alinhar_por_preenchimento` de `l2scanner.mercado_leitura` no bloco de import que ja
   existe, e escrever no comentario vizinho por que um simbolo privado de producao e
   importado em vez de a ferramenta padronizar o proprio alinhamento: a mecanica so pode
   ter uma casa, e uma segunda copia mediria outra coisa com o mesmo nome — a razao ja
   escrita para o portao de layout, aplicada de novo.

2. Sob a MESMA chave `--por-rotulo`, imprimir uma linha com os dois pares medidos na hora,
   usando os moldes de producao por `glifos_de_calibracao(cal)` — o mesmo acessor que
   `varrer` ja usa. Formato: os valores de `9`x`4` e de `0`x`8` lado a lado, com `0`x`8`
   nomeado como o par mais estreito do sistema. Se algum dos quatro rotulos faltar nos
   moldes, dizer qual faltou e seguir; nunca inventar o numero.

3. AS TRES REFUTACOES, na docstring do modulo, em secao propria. Elas sao o motivo da
   task existir e nao podem sair diluidas:

   REFUTACAO 1 — os moldes `9` e `4` NAO se parecem. Medido em 2026-09-02 com
   `casamento_da_ancora`, molde contra molde, na mesma mecanica da matriz de colisao:
   `9`x`4` = 0,3162 acromatico (posicao 19 de 78 pares) e 0,3788 cromatico (posicao 13),
   contra `0`x`8` = 0,7110, que e o par mais estreito do conjunto. Escrever que a
   ferramenta agora REMEDE isto a cada execucao sob `--por-rotulo`, e que
   `TestOsMoldesQueNaoSeParecem` prende a ordem em clone limpo — a afirmacao nao pode
   apodrecer em silencio.

   REFUTACAO 2 — a coluna do incremento NAO e cortada pela borda da janela. Medido em
   frame vivo: ela termina em x=1179 numa janela de 1720 de largura, 541 px de folga.
   Escrever o metodo junto do numero, para a medida ser refazivel sem adivinhacao.

   REGISTRO 3 — o arnes que foi JOGADO FORA, e por que este relatorio entrou na ferramenta
   existente. Um script avulso recalculou a geometria da celula A MAO em vez de usar a
   geometria de PRODUCAO. Ele devolveu resultado IDENTICO para as dez linhas de uma
   pagina — impossivel com dado real. As coordenadas caiam na coluna `Auction List`, cujo
   texto (`10,000,000 Adena`) e o mesmo em toda linha. E o mesmo padrao de defeito que
   esta sessao ja contou doze vezes, cometido desta vez por quem orquestrava. E
   exatamente por isso este trabalho entrou na ferramenta que JA usa geometria de
   producao, em vez de num script novo.

4. Os tres testes na classe `TestOsMoldesQueNaoSeParecem`, com docstring de classe dizendo
   que a classe existe para a REFUTACAO nao virar prosa que ninguem confere.

5. RODAR A FERRAMENTA DE VERDADE, no interpretador dela, sem gravar:
   `.venv/Scripts/python.exe tools/medir_leitura_de_glifo.py --por-rotulo`
   A varredura das 8 gravacoes leva minutos; e o trabalho normal dela. Copiar a tabela por
   rotulo inteira para o corpo do commit e, com base nos numeros das linhas do `9` e do
   `4`, escrever no commit se o `9` sai ACUSADO ou INOCENTADO — citando a taxa de recusa,
   o `score_p1` e o `margem_p1` das duas linhas. Se os numeros nao decidirem, dizer isso e
   dizer qual medicao decidiria; um veredito inventado seria pior que nenhum.
  </action>

  <verify>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_medir_leitura_de_glifo.py -v -k "TestOsMoldesQueNaoSeParecem"
    </automated>
    <automated>
python -c "import importlib.util,sys,pathlib,inspect; p=pathlib.Path('tools/medir_leitura_de_glifo.py'); s=importlib.util.spec_from_file_location('m',p); m=importlib.util.module_from_spec(s); sys.modules['m']=m; s.loader.exec_module(m); d=inspect.getdoc(m); assert '0,3162' in d and '0,7110' in d and '1179' in d and '1720' in d and 'Auction List' in d, 'faltou uma das tres refutacoes na docstring do modulo'; print('as tres refutacoes estao no fonte')"
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_medir_leitura_de_glifo.py
    </automated>
    <automated>
git diff --name-only HEAD | python -c "import sys; mudados=[l.strip() for l in sys.stdin if l.strip()]; assert sorted(mudados)==['tests/test_medir_leitura_de_glifo.py','tools/medir_leitura_de_glifo.py'], mudados; print('so a ferramenta e o teste dela:', sorted(mudados))"
    </automated>
    <human-check>
A tabela por rotulo de uma execucao REAL (`--por-rotulo`, sem `--gravar`) esta colada no
corpo do commit, e o veredito sobre o `9` — acusado, inocentado, ou indecidido com a
proxima medicao nomeada — esta escrito com os numeros que o sustentam.
    </human-check>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py
    </automated>
  </verify>

  <prova_por_mutacao>
OBRIGATORIA e nao opcional. Depois de a task estar VERDE:

1. Em `casamento_entre_moldes`, fazer a funcao comparar `moldes[a]` contra `moldes[a]`,
   ignorando `b` — os dois pares passam a valer 1,0.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestOsMoldesQueNaoSeParecem" -v`.
3. Confirmar VERMELHO nos Testes 1 e 2, e VERDE no Teste 3 (a ancora de sanidade nao
   distingue este caso, e e por isso que ela sozinha nunca bastaria).
4. COPIAR A LINHA DE RESUMO DO PYTEST VERBATIM para o corpo do commit.
5. Reverter a mutacao e reconfirmar o verde.
  </prova_por_mutacao>

  <mutacao_de_CONTROLE>
OBRIGATORIA, e ela tem de ficar VERDE.

1. Reescrever `casamento_entre_moldes` com a mesma semantica noutra forma: trocar
   `return float(casamento_da_ancora(*_alinhar_por_preenchimento(x, y)))` por duas linhas
   com locais nomeados (`a_alinhado, b_alinhado = ...` e depois o `return`), ou o
   contrario. NAO trocar a ordem dos argumentos: `casamento_da_ancora` nao e assumida
   simetrica, e inverter os argumentos seria uma mutacao de comportamento disfarcada de
   refatoracao.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestOsMoldesQueNaoSeParecem" -v`.
3. Confirmar VERDE. Se cair, o teste esta preso a forma do codigo e e o TESTE que se
   reescreve.
4. COPIAR A LINHA DE RESUMO VERBATIM para o corpo do commit.
5. Reverter e reconfirmar o verde.
  </mutacao_de_CONTROLE>

  <done>
- `casamento_entre_moldes` existe compondo os dois simbolos de PRODUCAO, e o Teste 2 prova
  a composicao por igualdade de valor.
- Os tres testes da classe passam, com os dois numeros medidos nas fixturas escritos
  verbatim na docstring, com data.
- As tres refutacoes estao na docstring do modulo com os numeros (0,3162 / 0,3788 / 0,7110;
  x=1179 em 1720, 541 px; as dez linhas identicas na coluna `Auction List`).
- A linha `9`x`4` contra `0`x`8` sai impressa sob `--por-rotulo`, medida na execucao.
- Uma execucao REAL da ferramenta, sem `--gravar`, com a tabela por rotulo e o veredito
  sobre o `9` no corpo do commit.
- `git diff --name-only HEAD` lista exatamente dois caminhos, os dois desta task.
- As duas mutacoes rodadas, com os resumos copiados verbatim.
- Suite completa na base medida no inicio da Task 1.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| disco -> ferramenta | `recordings/` e `calibration.json` sao estado de maquina lido pela varredura |
| ferramenta -> disco | `--gravar` e o unico caminho de escrita, e esta task o proibe |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-syn-01 | Tampering | `gravar()` sobre `calibration.json` | critical | mitigate | `--gravar` proibido pelas restricoes; o teste de padrao da chave afirma `.gravar is False`; nenhuma task chama `gravar` |
| T-syn-02 | Tampering | `.mercado/` (dado vivo do usuario) | high | mitigate | nenhum caminho deste plano escreve fora de `tools/` e `tests/`; o portao de `git diff --name-only` prova a lista exata |
| T-syn-03 | Information Disclosure | `calibration.json` num commit | high | mitigate | portao de `git diff --name-only` afirma que o arquivo nao aparece entre os mudados |
| T-syn-04 | Denial of Service | varredura ampla de `recordings/` | medium | mitigate | reusa a varredura NOMEADA de 8 gravacoes que ja existe; nenhum glob novo entra |
| T-syn-05 | Repudiation | refutacao vira prosa que apodrece | medium | mitigate | `TestOsMoldesQueNaoSeParecem` remede a afirmacao 1 em clone limpo, e o relatorio a remede a cada execucao |
| T-syn-SC | Tampering | instalacao de pacote | low | accept | nenhuma dependencia nova entra; nao ha instalacao a auditar |
</threat_model>

<verification>
- Base da suite MEDIDA antes da primeira linha e anotada; ao fim, igual a ela mais os
  testes novos, sem nenhuma regressao.
- `python -m pytest -q --ignore=tests/test_agenda.py` completo.
- `git diff --name-only HEAD` lista exatamente `tools/medir_leitura_de_glifo.py` e
  `tests/test_medir_leitura_de_glifo.py`.
- Quatro provas rodadas: duas mutacoes que tem de QUEBRAR e duas de CONTROLE que tem de
  SEGURAR, com os quatro resumos de pytest copiados verbatim nos commits.
- Uma execucao real com `--por-rotulo` e sem `--gravar`, com a tabela e o veredito sobre o
  `9` registrados.
</verification>

<success_criteria>
O `9` deixa de ser suspeito por palpite. Ou os numeros do balde dele o inocentam e a busca
se muda para a segmentacao e para a geometria da coluna, ou a cauda de margem baixa do
balde do `4` o acusa e ha `(gravacao, arquivo, linha, coluna)` para reconferir frame a
frame. E as tres coisas que ja foram tentadas e refutadas ficam escritas onde a proxima
pessoa esbarra nelas antes de repeti-las.
</success_criteria>

<output>
Criar `.planning/quick/260902-syn-a-medicao-de-glifo-passa-a-relatar-score/260902-syn-SUMMARY.md` ao terminar.
</output>
