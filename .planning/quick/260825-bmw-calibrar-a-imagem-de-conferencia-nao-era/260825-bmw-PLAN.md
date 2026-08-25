---
phase: quick-260825-bmw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/calibrar.py
  - tests/test_conferencia_gravada.py
autonomous: true
requirements: [QUICK-260825-bmw]

estimate:
  tokens: 50000
  raw_tokens: 25000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Quando o arquivo padrao de conferencia nao pode ser escrito, o calibrador grava um alternativo com horario no nome e diz ao usuario que o principal estava travado."
    - "Quando nem o alternativo pode ser escrito, o calibrador diz que NAO ha imagem de conferencia e nao imprime nome de arquivo nenhum."
    - "Toda mensagem de conferencia traz o caminho COMPLETO e o HORARIO do arquivo que foi realmente escrito."
    - "Os dois pontos de gravacao (party window e barra solo) passam pelo mesmo auxiliar — ha um unico ponto de escrita no modulo."
    - "O bloco final do modo --solo so manda o usuario conferir a imagem se uma imagem existir."
  artifacts:
    - "l2scanner/calibrar.py — funcao _gravar_conferencia(imagem) -> Path | None"
    - "tests/test_conferencia_gravada.py — regressao que falha no codigo atual"
  key_links:
    - "conferir_visualmente -> _gravar_conferencia (ponto de gravacao da party window)"
    - "_conferencia_do_solo -> _gravar_conferencia, com o retorno subindo ate o bloco --solo de main()"
    - "_gravar_conferencia -> RAIZ (global do modulo, para o teste poder redirecionar a escrita para tmp_path)"
---

<objective>
Fazer o calibrador parar de mentir sobre a imagem de conferencia.

Hoje `cv2.imwrite` e chamado em dois lugares e o retorno e jogado fora nos dois. Quando
a escrita falha — o gatilho real e o proprio usuario ter ABERTO a imagem no visualizador
de fotos, como o calibrador mandou — a funcao devolve `False`, cospe um `[ WARN:0 ]` no
stderr que se perde, e o calibrador imprime "Imagem de conferencia: ..." como se tivesse
dado certo. O usuario confere A IMAGEM VELHA e valida uma calibracao errada.

Isso ja foi CONFIRMADO nesta maquina: destino somente-leitura, destino ocupado por um
diretorio e pasta inexistente — os tres devolvem `False` e nenhum levanta excecao.

Purpose: numa ferramenta cujo unico trabalho e dizer "confie nisto", falhar em silencio
e a pior falha possivel. O calibrador precisa ou entregar uma imagem nova, ou dizer alto
que nao entregou.
Output: um unico auxiliar de gravacao com fallback e mensagem honesta, mais um teste de
regressao que falha no codigo de hoje.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@l2scanner/calibrar.py
@tests/test_visao.py

Convencao do projeto, obrigatoria aqui: comentarios, docstrings, nomes de teste e texto
de tela em PORTUGUES SEM ACENTOS no codigo. Comentarios explicam o PORQUE, citando a
falha real que motivou o codigo — veja `achar_barra_do_proprio` em `calibrar.py:222-239`
como o padrao de voz a seguir. Nada de identificador em ingles, nada de comentario seco.

Fatos medidos nesta maquina (nao precisa remedir):
- `cv2.imwrite` para um destino somente-leitura devolve `False`, sem excecao.
- `cv2.imwrite` para um caminho ocupado por um DIRETORIO devolve `False`, sem excecao.
- `cv2.imwrite` para uma pasta inexistente devolve `False`, sem excecao.
- `python -m pytest` funciona na raiz do repo (Python 3.12 do sistema, pytest 9.1.1).
- `.gitignore` ja ignora `*.png`, entao o arquivo alternativo nao suja o repositorio.
- `tests/fixtures/calibracao_de_referencia.json` existe e carrega com
  `Calibracao.carregar`, mas tem `hp_proprio: null` — o teste do modo solo precisa
  atribuir uma `Regiao` a mao.
- `Calibracao` e dataclass mutavel (o `main()` ja atribui `cal.janela`).
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: um unico ponto de escrita, com fallback e mensagem honesta</name>
  <files>tests/test_conferencia_gravada.py, l2scanner/calibrar.py</files>
  <precondition>`python -m pytest --version` responde na raiz do repo — a `.venv` do projeto nao tem pytest, o `python` do sistema tem. Se nao responder, pare e diga qual interpretador falta.</precondition>
  <reversibility rating="reversible">Mexe so no caminho de gravacao e nas mensagens de tela do calibrador; nenhum formato de arquivo, nenhuma assinatura consumida por outro modulo alem do proprio `main()`.</reversibility>
  <behavior>
Escreva PRIMEIRO `tests/test_conferencia_gravada.py`, rode, e confirme que ele falha no
codigo de hoje. O teste que precisa falhar antes de existir a correcao e o de regressao
(o quarto da lista). Todos os testes redirecionam a escrita com
`monkeypatch.setattr(l2scanner.calibrar, "RAIZ", tmp_path)`.

  - Gravacao normal: `_gravar_conferencia(imagem)` devolve o caminho de
    `calibracao-conferencia.png` dentro de RAIZ, e o arquivo existe e volta a ser lido
    por `cv2.imread`.
  - Destino travado (arquivo somente-leitura, via `os.chmod(caminho, stat.S_IREAD)` —
    e a simulacao fiel do visualizador de fotos segurando o arquivo): o retorno NAO e
    None, o nome casa `calibracao-conferencia-\d{6}\.png`, o arquivo existe e e uma
    imagem legivel, e o arquivo antigo continua intacto. Devolva o modo de escrita no
    fim do teste (`stat.S_IWRITE`) para o `tmp_path` poder ser limpo. Se o SO ignorar o
    somente-leitura e a gravacao padrao passar assim mesmo, `pytest.skip` com a razao.
  - Destino travado por DIRETORIO ocupando o nome: mesmo resultado do caso acima. Este e
    o caso deterministico em qualquer SO.
  - REGRESSAO (o que falha hoje): com RAIZ apontando para uma pasta inexistente
    (`tmp_path / "pasta-que-nao-existe"`), nada pode ser escrito. Chame
    `conferir_visualmente(cal, pixels, ox, oy)` e capture a saida com `capsys`. Extraia
    da saida todo nome terminado em `.png` e afirme que CADA um deles corresponde a um
    arquivo que existe no disco. No codigo atual sai `calibracao-conferencia.png` sem
    arquivo nenhum — e por ai que o teste falha. Afirme tambem que a saida avisa que nao
    ha imagem de conferencia.
  - Falta de imagem e reportada: no mesmo cenario, `_gravar_conferencia` devolve None.
  - O caminho e o horario aparecem: no caso de gravacao normal, a saida contem o caminho
    ABSOLUTO do arquivo escrito (nao so o nome) e um horario no formato `HH:MM:SS`.
  - Ponto de escrita unico: um teste estrutural que compara
    `inspect.getsource(l2scanner.calibrar).count("imwrite")` com
    `inspect.getsource(l2scanner.calibrar._gravar_conferencia).count("imwrite")` e exige
    que sejam iguais — se alguem duplicar a gravacao de novo, o teste cai.

Para montar `cal` e `pixels` do teste de regressao, carregue
`tests/fixtures/calibracao_de_referencia.json` com `Calibracao.carregar` e fabrique os
pixels com numpy no tamanho da `party_window` (o conteudo nao importa; o que se afirma e
a MENSAGEM, nao o desenho). Passe `ox`/`oy` coerentes com o retangulo.
  </behavior>
  <action>
Depois que o teste falhar, implemente em `l2scanner/calibrar.py`:

1. `_gravar_conferencia(imagem) -> Path | None`, colocada logo acima de
   `conferir_visualmente`. Ela e o UNICO lugar do modulo que escreve imagem — nenhuma
   outra funcao pode voltar a chamar a gravacao direto, e o docstring deve dizer por que
   (a duplicacao foi o que permitiu os dois pontos ignorarem o retorno em silencio).
   Estrutura: uma funcao interna que recebe um `Path`, tenta a gravacao dentro de
   `try/except Exception`, e devolve `bool` — assim tanto o `False` documentado quanto
   uma excecao inesperada caem no mesmo caminho de falha. A funcao externa tenta
   `RAIZ / "calibracao-conferencia.png"`; se falhar, avisa em linguagem de gente que o
   arquivo principal esta travado e sugere fechar o visualizador de fotos, e tenta
   `RAIZ / f"calibracao-conferencia-{time.strftime('%H%M%S')}.png"`; se as duas falharem,
   diz que NAO ha imagem de conferencia e devolve None.
   Leia `RAIZ` como global no corpo da funcao (nao capture em argumento com valor
   padrao), senao o teste nao consegue redirecionar a escrita.
2. Sucesso imprime o caminho ABSOLUTO e o HORARIO reais do que foi escrito — o horario
   sai de `caminho.stat().st_mtime` formatado com `time.strftime("%H:%M:%S", ...)`, nao
   do relogio no momento da chamada. O comentario deve dizer por que: a pergunta que o
   usuario faz olhando a tela e "essa imagem e nova?", e so o mtime do arquivo responde.
3. `conferir_visualmente` (linha ~435) passa a chamar o auxiliar e a condicionar TODO o
   texto seguinte ao retorno: com caminho, imprime a legenda de cores e manda abrir
   aquele caminho; sem caminho, diz que a conferencia visual nao aconteceu e que os
   numeros impressos acima sao tudo o que ha para conferir.
4. Nao mexa ainda em `_conferencia_do_solo` — e a Task 2.

Nao use "por enquanto", "versao simples" nem qualquer variacao: o fallback com horario e
a mensagem de ausencia entram agora, inteiros.
  </action>
  <verify>
    <automated>cd C:/Users/refun/Desktop/Lineage2-warnings && python -m pytest tests/test_conferencia_gravada.py -q</automated>
    <automated>cd C:/Users/refun/Desktop/Lineage2-warnings && python -c "import inspect, l2scanner.calibrar as c; t=inspect.getsource(c).count('imwrite'); h=inspect.getsource(c._gravar_conferencia).count('imwrite'); print(t,h); assert t==h and h>=1, 'ha gravacao de imagem fora do auxiliar'"</automated>
  </verify>
  <done>
`tests/test_conferencia_gravada.py` existe, foi visto FALHANDO antes da correcao (registre
no SUMMARY a mensagem de falha), e agora passa inteiro. `_gravar_conferencia` e o unico
ponto de escrita do modulo. Com o destino travado sai um arquivo com horario no nome e um
aviso claro; sem nenhum destino gravavel a saida nao contem nome de arquivo inexistente.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: o modo solo pelo mesmo auxiliar, e o bloco final para de prometer imagem</name>
  <files>l2scanner/calibrar.py, tests/test_conferencia_gravada.py</files>
  <behavior>
Acrescente ao mesmo arquivo de teste:

  - `_conferencia_do_solo(cal, pixels)` com destino travado devolve o caminho alternativo
    (com horario), e a saida nao cita nenhum `.png` que nao exista no disco. Monte o `cal`
    a partir de `tests/fixtures/calibracao_de_referencia.json` atribuindo
    `cal.hp_proprio = Regiao(...)` a mao — o fixture grava `null` nesse campo.
  - `_conferencia_do_solo` sem nenhum destino gravavel devolve None e a saida diz que nao
    ha imagem.
  - O bloco final do `--solo` nao manda conferir imagem que nao existe: um teste que
    afirme que a frase de "CONFIRA a imagem" so aparece quando ha caminho. Se isolar o
    bloco de `main()` sair caro, extraia essas linhas para uma funcao pequena que receba
    `Path | None` e teste a funcao — extrair e preferivel a nao testar.
  </behavior>
  <action>
1. `_conferencia_do_solo` (linha ~448) para de gravar por conta propria: desenha o
   retangulo e o rotulo como hoje, delega a gravacao a `_gravar_conferencia` e passa a
   devolver `Path | None`.
2. O bloco `--solo` de `main()` (linhas ~678-690) consome esse retorno. Hoje a linha
   "CONFIRA a imagem calibracao-conferencia.png antes de confiar" e imprimida
   incondicionalmente, com o nome do arquivo escrito a mao no codigo — ela precisa citar
   o caminho realmente gravado e so aparecer quando houver um. Sem imagem, o texto muda
   para dizer que a conferencia visual nao aconteceu e que o retangulo NAO foi conferido
   por ninguem — o alerta sobre a barra do alvo selecionado continua valendo e fica ainda
   mais importante.
3. O `try/except` que ja envolve a chamada em `main()` fica onde esta: ele cobre falha ao
   DESENHAR (recorte fora da tela, por exemplo), que e um problema diferente de falha ao
   gravar. Deixe um comentario dizendo isso, para o proximo leitor nao remover achando
   que virou redundancia.
4. Rode a suite inteira: nenhum dos 446 testes existentes pode quebrar.
  </action>
  <verify>
    <automated>cd C:/Users/refun/Desktop/Lineage2-warnings && python -m pytest tests/ -q</automated>
    <automated>cd C:/Users/refun/Desktop/Lineage2-warnings && python -c "import inspect, l2scanner.calibrar as c; t=inspect.getsource(c).count('imwrite'); h=inspect.getsource(c._gravar_conferencia).count('imwrite'); print(t,h); assert t==h, 'o modo solo voltou a gravar por conta propria'"</automated>
  </verify>
  <done>
Os dois pontos de gravacao passam pelo mesmo auxiliar. O bloco `--solo` de `main()` so
manda conferir imagem quando existe imagem, e cita o caminho real. Suite inteira verde.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| processo -> sistema de arquivos | O calibrador escreve uma imagem da TELA DO USUARIO no disco; e a unica saida do modulo |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-01 | Information disclosure | `_gravar_conferencia` | low | mitigate | O destino e sempre derivado de `RAIZ`, nunca de entrada do usuario; o nome alternativo e so um sufixo de horario. Nenhum caminho externo entra na funcao. `*.png` ja esta no `.gitignore`, entao a tela do usuario nao vaza para o repositorio |
| T-quick-02 | Tampering | nome alternativo por horario | low | accept | Duas rodadas no mesmo segundo colidiriam e a segunda sobrescreveria a primeira. Irrelevante: a imagem e descartavel e o usuario nao roda o calibrador duas vezes no mesmo segundo |
| T-quick-03 | Denial of service | fallback de gravacao | low | accept | Cada rodada travada deixa mais um `calibracao-conferencia-HHMMSS.png` na raiz. Sao poucos KB e ignorados pelo git; limpar automaticamente arriscaria apagar justamente a imagem que o usuario esta olhando |

Nenhum pacote novo e instalado neste plano — `cv2`, `time`, `pathlib` e `os` ja estao no
projeto, entao o portao de legitimidade de pacotes nao se aplica.
</threat_model>

<verification>
1. `python -m pytest tests/ -q` — suite inteira verde (446+ testes).
2. O teste de regressao foi visto FALHANDO no codigo pre-correcao, e a mensagem de falha
   esta registrada no SUMMARY. Sem isso o teste nao prova nada.
3. `grep -rn "imwrite" l2scanner/calibrar.py` — todas as ocorrencias dentro de
   `_gravar_conferencia`.
4. Conferencia manual do texto: nenhuma mensagem do calibrador cita nome de arquivo que
   ele nao acabou de escrever.
</verification>

<success_criteria>
- Destino travado: sai `calibracao-conferencia-HHMMSS.png` mais um aviso dizendo que o
  principal estava travado e sugerindo fechar o visualizador.
- Nenhum destino gravavel: o calibrador diz que NAO ha imagem de conferencia, e nao
  imprime nome de arquivo nenhum.
- Sucesso: caminho ABSOLUTO e horario do arquivo realmente escrito, tirado do mtime.
- Um unico ponto de escrita no modulo, protegido por teste estrutural.
- 446+ testes existentes continuam passando.
</success_criteria>

<output>
Create `.planning/quick/260825-bmw-calibrar-a-imagem-de-conferencia-nao-era/SUMMARY.md` when done
</output>
