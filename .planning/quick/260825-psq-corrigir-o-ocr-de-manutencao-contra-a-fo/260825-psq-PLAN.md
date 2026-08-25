---
phase: quick-260825-psq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/ocr.py
  - l2scanner/manutencao.py
  - l2scanner/calibracao.py
  - l2scanner/__main__.py
  - tests/test_ocr.py
  - tests/test_manutencao.py
autonomous: true
requirements: [QUICK-260825-psq]

estimate:
  tokens: 48000
  raw_tokens: 48000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Os dois textos REAIS observados nunca mais produzem 26 segundos: o embaralhado (`__40nin? es`) devolve None e o com `40ninutes` devolve 0:40:26 (D-b, D-c)"
    - "A fixture real `tests/fixtures/manutencao/banner_40min26s.png` lida ponta a ponta no `.venv` devolve 0:40:26 — nao 0:00:26 (D-a)"
    - "Nenhuma manutencao e anunciada sem que DUAS escalas de OCR concordem sobre o MESMO frame (D-d)"
    - "A passada cara (cinza 3x, 308 ms) nao roda quando a passada barata nao ve a raiz `mainten` (D-e)"
    - "A faixa padrao derivada da calibracao real do usuario (topo=222) cobre o banner estimado em y~168..253 com folga de dezenas de pixels em cima e embaixo (D-f)"
    - "A suite inteira continua passando no Python do SISTEMA, que nao tem as bindings de WinRT"
  artifacts:
    - l2scanner/ocr.py
    - l2scanner/manutencao.py
    - l2scanner/calibracao.py
    - tests/test_ocr.py
    - tests/test_manutencao.py
  key_links:
    - "`ocr.ler_texto` (barata) e `ocr.ler_texto_ampliado` (cara) injetadas no `VigiaDeManutencao` por `montar_vigia_de_manutencao`"
    - "`interpretar_banner` -> `VigiaDeManutencao._registrar`: a duracao que vira ancora no relogio"
    - "`Calibracao.regiao_do_banner` -> `frame.extras['banner_manutencao']` -> `obter_pixels` do vigia"
---

<objective>
O aviso de manutencao entregue ontem (quick 260825-onz) anunciaria **"MANUTENCAO em
26 segundos" quando faltam 40 minutos e 26 segundos**. Medido contra o screenshot
real do usuario, na fonte real do jogo, com a fixture ja salva no repo.

E o pior tipo de erro: plausivel. E o consenso que existe hoje NAO pega, porque
duas leituras pelo MESMO metodo com 5 s de intervalo concordam no MESMO erro
sistematico.

Purpose: fechar a unica limitacao que o SUMMARY de 260825-onz declarou em aberto
("a precisao do OCR na FONTE DO JOGO nao foi provada") — agora com a fonte real
na mao, e com guardas que fazem a leitura duvidosa CALAR em vez de mentir.

Output: `ocr.py` lendo em cinza e em duas escalas; `interpretar_banner` com uma
guarda estrutural que devolve None quando a unidade aparece sem numero;
`VigiaDeManutencao` exigindo que DUAS escalas concordem antes de alimentar o
consenso temporal; a faixa padrao do banner com folga vertical; e os textos
reais virando regressao permanente que roda sem OCR nenhum.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.claude/CLAUDE.md
@.planning/STATE.md
@.planning/quick/260825-onz-aviso-de-manutencao-do-servidor-lendo-o-/260825-onz-SUMMARY.md

@l2scanner/ocr.py
@l2scanner/manutencao.py
@l2scanner/calibracao.py
@tests/test_ocr.py
@tests/test_manutencao.py
</context>

<medicoes>
Estes numeros sao DADO DE ENTRADA. Nao repetir as medicoes — reproduzi-las nos
comentarios do codigo. Este projeto documenta numero medido, nao palpite.

**Precisao, contra `tests/fixtures/manutencao/banner_40min26s.png` (360x135, fonte
real do jogo, verdade = 40 min 26 s):**

| entrada                 | o OCR leu                                          | o parser deu |
|-------------------------|----------------------------------------------------|--------------|
| COR, imagem inteira     | `12 Server Maintence __40nin? es 26 seconds ...`   | 0:00:26 ERRADO |
| CINZA 1x (sem ampliar)  | `12 Server Maintence 40 minutes 26 seconds ...`    | 0:40:26 CERTO |
| CINZA 2x                | `12 Server Maintence 40ninutes 26 seconds ...`     | 0:00:26 ERRADO |
| CINZA 3x                | `Server Maintence 40 minutes 26 seconds ...`       | 0:40:26 CERTO |
| CINZA 4x                | `Server Maintence 40 minutes 26 seconds ...`       | 0:40:26 CERTO |

**Custo, na banda de producao 732x140:** 1x = 44 ms, 2x = 158 ms, 3x = 308 ms,
4x = 680 ms.

**As duas conclusoes que viraram decisao:**
1. Converter para CINZA e o que corrige o caso real, e custa zero.
2. A precisao NAO e monotonica na escala — 2x erra entre 1x e 3x que acertam.
   Logo NENHUMA escala unica e confiavel sozinha.

**Calibracao real do usuario (`calibration.json`, medida 2026-08-24):**
`party_window_na_janela` = esquerda 20, topo 222, largura 172, altura 522.
</medicoes>

<decisoes_travadas>
Nao revisitar, nao propor alternativas. Cite o identificador nas mensagens de
commit e nos comentarios.

- **D-a** — `ocr.ler_texto` converte para CINZA antes de reconhecer
  (`cv2.COLOR_BGR2GRAY` quando `ndim == 3`).
- **D-b** — GUARDA ESTRUTURAL em `interpretar_banner`: se aparecer no texto uma
  palavra de unidade de MINUTOS ou de HORAS mas nenhum numero puder ser extraido
  para ela, a leitura e INCONFIAVEL e a funcao devolve None. **JAMAIS cair para
  "entao e so os segundos"** — foi exatamente assim que 40min26s virou 26s.
- **D-c** — Casamento TOLERANTE da palavra de unidade, para recuperar as formas
  que o OCR produz DE VERDADE: `minutes`, `ninutes`, `40ninutes` (grudada no
  numero), `nin es`, `minut`. Idem para segundos. D-c resolve o caso do 2x e D-b
  resolve o caso da cor: sao complementares, nao alternativos.
- **D-d** — LEITURA EM DUAS ESCALAS. A passada BARATA (cinza 1x, 44 ms) roda
  sempre na cadencia e DETECTA a raiz `mainten`. So quando ela detecta, roda uma
  SEGUNDA passada em cinza 3x, e o anuncio exige que as DUAS ESCALAS concordem
  dentro da tolerancia.
- **D-e** — Orcamento: 44 ms a cada 5 s em regime permanente. A passada cara so
  existe durante a contagem regressiva, que e rara e limitada.
- **D-f** — A banda padrao ganha folga vertical: `MARGEM_ACIMA_DO_BANNER` 60 ->
  130 e `ALTURA_DA_FAIXA_DO_BANNER` 140 -> 240.
</decisoes_travadas>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Do PNG real ate 0:40:26 — cinza no OCR, guarda estrutural e tolerancia no parser</name>
  <files>l2scanner/ocr.py, l2scanner/manutencao.py, tests/test_manutencao.py, tests/test_ocr.py</files>
  <read_first>
    l2scanner/ocr.py (`_reconhecer`, `ESCALA`), l2scanner/manutencao.py
    (`_normalizar_digitos`, `interpretar_banner`, `_HORAS`/`_MINUTOS`/`_SEGUNDOS`,
    `_TROCAS`), tests/test_manutencao.py (`BANNER_REAL`, `TestLeituraDoBanner`),
    tests/test_ocr.py inteiro.
  </read_first>

  <behavior>
    Escreva estes testes ANTES da implementacao. Os tres primeiros nao tocam OCR
    nenhum e sao a regressao permanente:

    - `TEXTO_EMBARALHADO` = `"12 Server Maintence __40nin? es 26 seconds Please avoid entering instance Korzis O' Kaus"`
      -> `interpretar_banner` devolve **None** (D-b). Assercao explicita de que
      NAO devolve `timedelta(seconds=26)`, com o comentario dizendo que este era
      o bug.
    - `TEXTO_GRUDADO` = `"12 Server Maintence 40ninutes 26 seconds Please avoid entering instance ( 3>YKorzis"`
      -> devolve `timedelta(minutes=40, seconds=26)` (D-c).
    - `TEXTO_LIMPO` = `"12 Server Maintence 40 minutes 26 seconds Please avoid entering instance Korzis O' Kaus"`
      -> devolve `timedelta(minutes=40, seconds=26)`.
    - Teste DEDICADO da guarda D-b, parametrizado sobre as formas da unidade sem
      numero acoplado (`"Server Maintence nin es 26 seconds"`,
      `"Server Maintence __40nin? es 26 seconds"`,
      `"Server Maintence minutes 26 seconds"`): todas devolvem None, e o teste
      afirma `is None` — nao "um numero pequeno".
    - Teste de que a guarda NAO e uma rede que pega tudo: `"SERVER MAINTENCE 26 SECONDS"`
      (banner sem parte de minutos nenhuma) segue devolvendo 26 segundos.
    - `tests/test_ocr.py`: a fixture REAL lida ponta a ponta —
      `cv2.imread('tests/fixtures/manutencao/banner_40min26s.png')` ->
      `ocr.ler_texto` -> `eh_banner_de_manutencao` True e `interpretar_banner`
      == `timedelta(minutes=40, seconds=26)`.
  </behavior>

  <action>
    **1. `l2scanner/ocr.py` — cinza (D-a).** Em `_reconhecer`, antes do resize,
    converta com `cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)` quando
    `pixels.ndim == 3`. Um recorte que ja chega com um canal passa direto.
    Docstring/comentario registrando a medicao que motivou: na mesma fixture, em
    COR o motor leu `__40nin? es` e o parser deu 0:00:26; em CINZA leu
    `40 minutes` e deu 0:40:26. Diga tambem o porque: a fonte do banner e clara
    sobre fundo escuro e os canais BGR carregam variacao de cor que nao carrega
    informacao de FORMA — o motor gasta contraste com ela. E que custa zero:
    `cvtColor` sobre 732x140 e ruido perto dos 44 ms da propria passada.

    **2. `l2scanner/manutencao.py` — separar CAPTURA de PRESENCA.** Hoje ha um
    unico jogo de padroes que faz as duas coisas ao mesmo tempo, e e por isso que
    "unidade sem numero" some em silencio. Passe a ter dois jogos:

    Padroes de CAPTURA (numero + unidade), rodando sobre o texto NORMALIZADO:
    `_HORAS` = `r"(\d+)\s*h[o0]ur"`, `_MINUTOS` = `r"(\d+)\s*[mn]inut"`,
    `_SEGUNDOS` = `r"(\d+)\s*[5s]ec[o0]nd"` (D-c). A classe `[mn]` recupera
    `ninutes`; o `\s*` (zero ou mais) recupera `40ninutes` grudado; as classes
    `[o0]`/`[5s]` existem porque `_normalizar_digitos` traduz DENTRO de um token
    que ja tem digito — `26seconds` grudado vira `265ec0nd5`, e o retrocesso do
    regex ainda captura 26 ali.

    Padroes de PRESENCA (a unidade aparece, com ou sem numero):
    `_PALAVRA_DE_HORAS` = `r"h[o0]ur"` e `_PALAVRA_DE_MINUTOS` = `r"[mn]in"`.
    Comente que `[mn]in` e deliberadamente frouxo E comprovadamente seguro no
    contexto: nem `maintence` nem `maintenance` contem `min` ou `nin` (confira
    letra a letra no comentario), e o unico texto que chega aqui ja passou por
    `eh_banner_de_manutencao`. Registre a assimetria de custo que justifica a
    frouxidao: um falso positivo da presenca custa UMA leitura (5 s ate a
    proxima cadencia); um falso negativo faz 40 minutos virarem 26 segundos e a
    party inteira largar o farm. Registre tambem o preco aceito: se um nome de
    personagem ou um texto vizinho dentro da faixa contiver `min`/`nin`, a
    guarda dispara e a leitura se perde — de proposito, sempre para o lado
    seguro.

    A presenca da unidade de HORAS espelha a forma da de minutos sem inventar
    evidencia: o jogo anuncia com dezenas de MINUTOS e nunca foi observado
    embaralhando `hour`. Diga isso no comentario em vez de fingir uma medicao.

    **3. `interpretar_banner` — a guarda estrutural (D-b).** Reescreva o corpo
    nesta ordem, e documente a ordem:
    - `cru` = `texto.lower()` (SEM normalizar).
    - `normalizado` = `_normalizar_digitos(texto).lower()` (como hoje).
    - Busque as tres CAPTURAS em `normalizado`.
    - A PRESENCA e checada nos DOIS textos (`cru` e `normalizado`) e basta casar
      num deles. Motivo, que e o coracao da correcao: `_normalizar_digitos` so
      transforma tokens que ja tem digito, entao um `40MINUTES` grudado viraria
      `40m1nute5` e a unidade desapareceria do texto normalizado. Checar a
      presenca tambem no texto CRU garante o invariante que queremos: a
      normalizacao so pode nos custar uma leitura, nunca nos dar uma leitura
      ERRADA.
    - Se ha presenca de HORAS e a captura de horas falhou -> devolva None. Idem
      para MINUTOS. A guarda vem ANTES de somar qualquer componente, senao a
      queda para "so os segundos" ja aconteceu.
    - So depois: soma, teto `_TETO`, retorno. `timedelta(0)` segue sendo
      resultado legitimo.

    A docstring de `interpretar_banner` deve carregar a medicao inteira: em COR
    o motor leu `__40nin? es 26 seconds`, o parser antigo achou `26 seconds`, nao
    achou minutos nenhum e devolveu 26 segundos com cara de resposta boa. A
    guarda existe para transformar exatamente esse desfecho em None. Deixe
    explicito que perder a leitura custa 5 segundos e anunciar manutencao
    iminente sem motivo custa a farm da party inteira.

    **4. Constantes de teste.** Em `tests/test_manutencao.py`, acrescente
    `TEXTO_EMBARALHADO`, `TEXTO_GRUDADO` e `TEXTO_LIMPO` ao lado de
    `BANNER_REAL`, com um cabecalho dizendo que sao saidas MEDIDAS do motor
    sobre a fixture real (e de qual passada cada uma veio), nao textos
    inventados. Corrija tambem o comentario de `BANNER_REAL`, que hoje diz
    "banner sintetico" — agora existe fonte real.

    **5. A fixture ponta a ponta em `tests/test_ocr.py`.** Calcule a condicao do
    skip UMA vez, no nivel do modulo (`TEM_OCR = ocr.disponivel()` e o motivo
    junto, seguido de `ocr._resetar_cache()` para nao poluir a fixture autouse
    que ja existe). Marque a classe com
    `@pytest.mark.skipif(not TEM_OCR, reason=...)`, e a razao precisa dizer o
    CONSERTO, no mesmo estilo de `SEM_BINDINGS`: que o Python do sistema nao tem
    as bindings e que este teste roda pelo `.venv`. Afirme o VEREDITO do parser,
    nunca o texto exato do OCR — o texto varia com a build do Windows, o
    veredito e o contrato. Um comentario deve dizer que sem a correcao de D-a
    este teste falharia com 0:00:26.
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py tests/test_ocr.py -q -rs</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && .venv/Scripts/python.exe -m pytest tests/test_ocr.py -q -rs</automated>
  </verify>

  <done>
    Com o Python do sistema a suite inteira passa (683 + os novos) e o teste da
    fixture aparece como **skipped com razao legivel** no `-rs` — nunca silencioso,
    nunca falho. Com o `.venv`, o teste da fixture **passa**: o PNG real de
    360x135 atravessa `ocr.ler_texto` e `interpretar_banner` e sai como
    `0:40:26`. Os tres textos reais estao no arquivo de teste como constantes e o
    embaralhado devolve None.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Duas escalas sobre o mesmo frame — a guarda que pega erro sistematico</name>
  <files>l2scanner/ocr.py, l2scanner/manutencao.py, l2scanner/__main__.py, tests/test_manutencao.py, tests/test_ocr.py</files>
  <read_first>
    l2scanner/manutencao.py (`VigiaDeManutencao.avaliar`, `_ler`, `_registrar`,
    `TOLERANCIA_DO_CONSENSO`), l2scanner/__main__.py (`montar_vigia_de_manutencao`
    por volta da linha 190, `comando_testar_manutencao` por volta da linha 984),
    tests/test_manutencao.py (`LeitorFalso`, `novo_vigia`, `rodar`, `TestCadencia`,
    `TestConsenso`, `TestMontagemNoArranque`), tests/test_ocr.py
    (`TestEntradaDegenerada`, `TestExcecaoDaPlataformaEEngolida`).
  </read_first>

  <behavior>
    Testes antes da implementacao, todos com leitores injetados (zero OCR):

    - Duas escalas que DISCORDAM alem da tolerancia nao anunciam nada e nao
      ancoram, mesmo repetidas por varios ticks. Este e o teste que reproduz o
      bug: a barata dizendo `TEXTO_LIMPO` (40 min) e a cara dizendo
      `"Server Maintence 26 seconds"` -> nada sai, `vigia.momento is None`.
    - Duas escalas que CONCORDAM alimentam o consenso temporal como sempre:
      duas leituras concordantes em ticks diferentes anunciam.
    - Uma discordancia entre duas leituras boas nao destroi a candidata nem a
      ancora ja confirmada (nem confirma, nem apaga).
    - A escala cara NAO e chamada quando a barata nao ve a raiz `mainten`
      (D-e): rode 12 ticks com texto de chat comum e afirme
      `leitor.chamadas_de_conferencia == 0` enquanto `leitor.chamadas == 3`.
    - A escala cara e chamada UMA vez por cadencia quando a barata detecta.
    - Fiacao: `montar_vigia_de_manutencao` devolve um vigia cujas duas escalas
      sao `ocr.ler_texto` e `ocr.ler_texto_ampliado`.
    - `tests/test_ocr.py`: a fixture real parseia para `0:40:26` **nas duas
      escalas** (`ler_texto` e `ler_texto_ampliado`), parametrizado.
  </behavior>

  <action>
    **1. `l2scanner/ocr.py` — duas escalas nomeadas.** Substitua a constante
    `ESCALA` por `ESCALA_DE_DETECCAO = 1` e `ESCALA_DE_CONFERENCIA = 3`. Exponha
    `ler_texto(pixels)` (deteccao) e `ler_texto_ampliado(pixels)` (conferencia);
    ambas passam a escala ao caminho interno, que ganha o parametro. Quando a
    escala e 1, **nao chame `cv2.resize` de forma alguma** — e dai que vem a
    diferenca medida entre 44 ms e 308 ms.

    Comentario obrigatorio com a tabela de custo medida em 732x140 (1x=44 ms,
    2x=158 ms, 3x=308 ms, 4x=680 ms) e com o motivo de 2x nunca aparecer aqui: na
    fixture real o 2x ERRA (0:00:26) entre 1x e 3x que ACERTAM — a precisao nao
    e monotonica na escala, e por isso nenhuma escala unica e confiavel sozinha.
    Registre o orcamento de D-e: 44 ms a cada 5 s sao 0,9% de um nucleo, mesma
    ordem do `matchTemplate` que o projeto ja aceita e documenta em `cliente.py`.

    Atualize os dois dubles de teste em `tests/test_ocr.py` que substituem a
    funcao interna de reconhecimento para a nova assinatura. Sem isso o teste da
    excecao passaria por engano — engolindo um erro de assinatura em vez do erro
    de plataforma que ele diz provar, e um teste que passa pelo motivo errado e
    pior que um teste ausente.

    **2. `VigiaDeManutencao` recebe DUAS leitoras.** Assinatura:
    `ler_texto` e `ler_texto_conferencia`, ambas OBRIGATORIAS. Obrigatorias, e
    nao opcionais com queda para uma so, porque a guarda de cruzamento e a razao
    de existir desta tarefa e um argumento opcional convida a que ela fique
    desligada em silencio. O vigia segue sem saber o que "escala" significa: ele
    recebe duas maneiras INDEPENDENTES de ler o mesmo recorte, e o modulo puro
    continua sem `cv2` e sem `ocr`.

    **3. A guarda de cruzamento, dentro do tick.** Extraia um passo privado que
    recebe o recorte e o instante e devolve o par (momento implicado, duracao)
    ou None. Sequencia:
    - Le com a BARATA. Se o texto nao tem a raiz `mainten`, devolve None sem
      tocar na cara (D-e).
    - Le com a CARA, sobre o MESMO recorte.
    - Exige que a cara tambem seja banner, que as DUAS produzam duracao e que os
      dois momentos implicados fiquem dentro de `TOLERANCIA_DO_CONSENSO`.
    - Qualquer reprovacao devolve None sem tocar em `_candidata` nem na ancora:
      uma discordancia nao confirma e tambem nao destroi.
    - Aprovado, vence a leitura de CONFERENCIA — e a que pagamos para ter, e a
      que as medicoes de 3x e 4x mostraram acertando.

    Ambas as leituras continuam passando pela protecao contra excecao que ja
    existe (este passo roda DENTRO do tick de captura).

    **4. Registro no log quando as escalas discordam.** Use `logging` da
    stdlib (permitido; os imports proibidos aqui seguem sendo `winrt`, `cv2` e
    `l2scanner.ocr`, e o teste de arvore com `ast` continua valendo). Emita
    `warning` com os DOIS textos crus entre delimitadores visiveis. Justifique no
    comentario: este evento significa "o banner esta na tela e nos NAO vamos
    anunciar", que e o estado mais perigoso deste recurso, e o log rotativo e a
    unica ferramenta de forense pos-farm do projeto. Escolha deliberada e
    registrada: nao ha limitacao de repeticao — durante uma contagem de 40
    minutos isso pode render centenas de linhas, e sao exatamente as linhas que o
    usuario vai precisar para consertar a faixa.

    **5. A escolha entre substituir e complementar o consenso temporal —
    documente-a na docstring da classe.** Fica **COMPLEMENTAR**, e a razao e que
    os dois consensos pegam falhas de classes diferentes. Cruzar escalas pega
    ERRO DE METODO (o motor lendo mal a mesma imagem — provado pela medicao: cor
    e 2x erram, 1x e 3x acertam) e o consenso temporal e cego a ele, porque duas
    leituras pelo mesmo metodo concordam no mesmo erro. Repetir no tempo pega
    ERRO DE FRAME (uma captura no meio do desenho do banner, um frame sujo) e o
    cruzamento de escalas e cego a ele, porque as duas escalas leem os MESMOS
    pixels. Guardar so um dos dois deixaria uma das duas classes descoberta.
    Custo de manter os dois: uma cadencia, 5 s numa contagem de 40 minutos.

    **6. `montar_vigia_de_manutencao` passa as duas leitoras**, e a linha de log
    de recurso ativo passa a dizer as duas escalas e o custo esperado, para que o
    arranque conte a verdade sobre o orcamento.

    **7. `comando_testar_manutencao` mostra as DUAS leituras.** E a ferramenta de
    conferencia humana da proxima manutencao real, e o desacordo entre escalas e
    justamente o que ela precisa expor. Imprima os dois textos crus entre
    delimitadores visiveis, os dois vereditos do parser, e uma linha final
    dizendo se as escalas concordam. Mantenha o comportamento atual de erro
    quando a leitura barata nao devolve nada.

    **8. Ajuste os dubles de `tests/test_manutencao.py`.** `LeitorFalso` ganha um
    metodo de conferencia com contador proprio e um texto de conferencia que
    ESPELHA `texto` por padrao — assim os testes de consenso temporal que ja
    existem seguem exercitando exatamente o que exercitavam (duas escalas que
    concordam trivialmente), e so os testes novos apontam os textos para lados
    diferentes. `novo_vigia` liga os dois lados no mesmo duble. O contador
    `chamadas` continua contando SO a passada barata, senao `TestCadencia`
    passaria a medir outra coisa sem ninguem perceber.
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py tests/test_ocr.py -q -rs</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py -q -k "Escala or Cruzament or Cadencia or Consenso or Montagem"</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && .venv/Scripts/python.exe -m pytest tests/test_ocr.py -q -rs</automated>
  </verify>

  <done>
    Duas escalas discordantes sobre o mesmo frame nao ancoram e nao anunciam,
    provado por teste sem OCR. A escala cara nao e chamada quando a barata nao ve
    a raiz `mainten`. `montar_vigia_de_manutencao` entrega o vigia com as duas
    leitoras do modulo de OCR. No `.venv`, a fixture real parseia `0:40:26` nas
    duas escalas. A suite inteira segue passando no Python do sistema.
  </done>
</task>

<task type="auto">
  <name>Task 3: Folga vertical na faixa do banner, medida contra a calibracao real</name>
  <files>l2scanner/calibracao.py, tests/test_manutencao.py</files>
  <read_first>
    l2scanner/calibracao.py (constantes por volta da linha 24-36 e
    `regiao_do_banner` por volta da linha 226), tests/test_manutencao.py
    (`TestRegiaoDoBanner` por volta da linha 444, incluindo o ajudante
    `_calibracao`).
  </read_first>

  <action>
    **1. As constantes (D-f).** `MARGEM_ACIMA_DO_BANNER` passa de 60 para 130 e
    `ALTURA_DA_FAIXA_DO_BANNER` de 140 para 240. As outras duas nao mudam.

    **2. O comentario passa de palpite a conta.** O bloco acima das constantes
    hoje se declara "um palpite educado, nao uma medicao". Reescreva com a conta
    real, porque agora ela existe: com a calibracao do usuario
    (`party_window_na_janela` topo=222), os numeros antigos davam a faixa
    y 162..302 na janela, e a estimativa do banner no screenshot cai em
    y~168..253 — folga de ~6 px no topo, contra uma estimativa que TEM incerteza.
    Errar por 6 px corta o titulo `Server Maintence`, que e literalmente o que
    `eh_banner_de_manutencao` procura, e o recurso inteiro cala. Com 130/240 a
    faixa vira y 92..332: ~76 px de folga em cima e ~79 embaixo.

    Registre a medicao que autoriza a folga: area extra **nao piora** a precisao
    — na fixture real, a imagem INTEIRA em cinza tambem leu 0:40:26. E registre o
    custo, marcando-o como EXTRAPOLACAO e nao medicao: a faixa sai de 732x140
    para 732x240, 1,71x pixels, o que sobre os 44 ms medidos projeta ~75 ms por
    passada barata — segue dentro do orcamento de D-e (a cada 5 s, pouco mais de
    1% de um nucleo). Diga que e projecao, nao numero medido.

    Acrescente uma frase sobre o preco novo que a folga cria, que e real e
    aceito: mais area significa mais texto vizinho dentro da faixa, e a guarda
    estrutural de D-b prefere calar a arriscar — se um texto vizinho trouxer uma
    forma que pareca unidade de minutos sem numero, a leitura se perde. Perder
    uma leitura custa 5 segundos; cortar o titulo custa o recurso inteiro.

    **3. Teste de regressao contra a calibracao REAL.** Em `TestRegiaoDoBanner`,
    acrescente um teste que monta a calibracao com os valores medidos do usuario
    (esquerda 20, topo 222, largura 172, altura 522, via o ajudante `_calibracao`
    que ja existe) e afirma que a faixa resultante cobre a estimativa do banner
    y 168..253 **com pelo menos 40 px de folga de cada lado**. A folga entra na
    assercao de proposito: cobrir por 1 px passaria no teste e falharia na tela,
    e a estimativa do banner tem incerteza. Comente que os numeros vem da
    calibracao real medida em 2026-08-24 e que estao inline porque
    `calibration.json` e ignorado pelo git — um teste que dependesse dele nao
    rodaria em clone nenhum.

    Confira que os testes vizinhos que ja existem seguem valendo com os numeros
    novos: o que exige cobrir o canto da party window e o que proibe coordenada
    negativa quando a party window esta colada no topo.
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py -q -k "RegiaoDoBanner"</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -c "from l2scanner import calibracao as c; assert (c.MARGEM_ACIMA_DO_BANNER, c.ALTURA_DA_FAIXA_DO_BANNER) == (130, 240), 'D-f nao aplicado'; assert c.VERSAO_DO_ESQUEMA == 2, 'o esquema nao pode subir por causa de constantes'; print('D-f ok')"</automated>
  </verify>

  <done>
    A faixa derivada da calibracao real cobre y 168..253 com dezenas de pixels de
    folga dos dois lados, provado por teste. `VERSAO_DO_ESQUEMA` continua em 2 —
    mudar constantes de derivacao nao pode invalidar o `calibration.json` que o
    usuario mediu a mao. A suite inteira passa.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pixels da tela -> `ocr.ler_texto` | Tudo que o jogo desenha na faixa entra aqui, inclusive texto escrito por OUTROS jogadores (chat, nomes) |
| texto do OCR -> `interpretar_banner` | String nao confiavel, embaralhada por um motor probabilistico, virando uma decisao que manda mensagem para a party |
| `VigiaDeManutencao` -> Chatwoot/WhatsApp | Um veredito errado vira mensagem irreversivel no grupo |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-psq-01 | Spoofing | `interpretar_banner` / `eh_banner_de_manutencao` | medium | accept | Um jogador escrevendo `Server Maintence 5 minutes` no chat, SE o chat cair dentro da faixa, produz um anuncio falso. Nenhuma guarda desta tarefa ajuda: o texto e legitimo em ambas as escalas e em ambos os ticks. Aceito e registrado; a faixa e derivada do TOPO da party window, onde o chat do XM Essence nao mora. |
| T-psq-02 | Tampering | `interpretar_banner` (dado embaralhado pelo OCR) | high | mitigate | E a ameaca central desta tarefa. Guarda estrutural D-b (unidade sem numero -> None), casamento tolerante D-c e acordo obrigatorio entre duas escalas D-d. Cada uma cobre uma classe de embaralhamento medida na fixture real. |
| T-psq-03 | Denial of Service | tick de captura (`Sessao._processar_manutencao`) | medium | mitigate | A passada de 3x custa 308 ms medidos e a faixa cresce 1,71x. Mitigado por D-e: a cara so roda quando a barata ve `mainten`, e a barata roda a 0,2 Hz. A protecao contra excecao dentro do tick continua valendo nas DUAS leituras — nenhuma falha de OCR pode parar o scanner de olhar a party. |
| T-psq-04 | Information Disclosure | log rotativo (`l2scanner.log`) | low | accept | O `warning` de escalas discordantes grava o texto cru da faixa, que pode conter nomes de personagens e texto vizinho. Log local, rotativo (5 MB x 3), e a unica ferramenta de forense pos-farm do projeto. |
| T-psq-05 | Repudiation | anuncio sem rastro | low | mitigate | Toda rejeicao por desacordo de escalas fica no log com os DOIS textos crus, entao "por que nao avisou" tem resposta em arquivo. |
| T-psq-SC | Tampering | instalacao de pacotes | n/a | accept | **Esta tarefa nao instala pacote nenhum.** `winrt-*`, `opencv-python` e `numpy` ja estao no `requirements.txt` desde 260825-onz; `requirements.txt` nao e tocado. Nenhum portao de legitimidade de pacote se aplica. |
</threat_model>

<verification>
Ordem de conferencia, do mais barato ao mais caro:

1. `python -m pytest -q` no Python do SISTEMA — a suite inteira passa (683 antes
   desta tarefa, mais os novos). Este e o item mais importante: prova que o
   caminho sem bindings de OCR segue sendo o caminho padrao da suite.
2. `python -m pytest tests/test_ocr.py -q -rs` — o teste da fixture aparece como
   **skipped com razao legivel**. Nao pode sumir, nao pode falhar.
3. `.venv/Scripts/python.exe -m pytest tests/test_ocr.py -q -rs` — o teste da
   fixture **passa**, nas duas escalas, com veredito `0:40:26`.
4. `python -m pytest tests/test_manutencao.py -q` — a guarda D-b, a tolerancia
   D-c, o cruzamento de escalas D-d e a faixa D-f, todos sem OCR nenhum.
5. Ortogonalidade: `git diff --stat` nao pode listar `visao.py`, `rastreador.py`,
   `identidade.py`, `agenda.py` nem `sessao.py`. O contrato de `avaliar` nao muda,
   entao a costura no `Sessao` nao e tocada.
</verification>

<success_criteria>
- O texto real embaralhado (`__40nin? es 26 seconds`) devolve **None**, nao 26
  segundos, e ha um teste que afirma isso nominalmente.
- O texto real grudado (`40ninutes 26 seconds`) devolve **0:40:26**.
- A fixture `tests/fixtures/manutencao/banner_40min26s.png` atravessa OCR e
  parser e sai como **0:40:26** no `.venv`, nas duas escalas.
- Nenhum anuncio sai sem acordo entre duas escalas sobre o mesmo frame.
- A escala cara nao roda quando a barata nao ve `mainten`.
- A faixa padrao cobre o banner estimado com dezenas de pixels de folga.
- 683 testes continuam passando, mais os novos, no Python sem OCR.
- Todo numero citado em comentario e medido ou explicitamente marcado como
  extrapolacao.
</success_criteria>

<human_verification>
<human-check>
Na PROXIMA MANUTENCAO REAL (ou com o PNG de uma), rodar
`vigiar-party.bat --testar-manutencao` com o banner na tela e conferir, na saida:

1. Os DOIS textos crus, entre delimitadores — e se as escalas concordam.
2. O veredito do parser batendo com o numero que esta na tela.
3. Se as escalas discordarem, o `l2scanner.log` tem a linha de `warning` com os
   dois textos: e ela que diz se o conserto e a faixa (chave `banner_manutencao`
   no `calibration.json`) ou o motor.

Item pendente herdado de 260825-onz e ainda valido: conferir que o recorte
gravado em `logs/` pega o lugar onde o banner aparece — agora com a faixa mais
alta.
</human-check>
</human_verification>

<output>
Create `.planning/quick/260825-psq-corrigir-o-ocr-de-manutencao-contra-a-fo/260825-psq-SUMMARY.md` when done
</output>
