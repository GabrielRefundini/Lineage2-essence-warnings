---
phase: quick-260830-bvo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/config.py
  - l2scanner/calibrar.py
  - config.toml
  - tests/test_mira_da_janela.py
  - tests/test_calibrar_nao_apaga_mercado.py
autonomous: true
requirements: [MIRA-01, MIRA-02]

estimate:
  tokens: 66000
  raw_tokens: 66000
  tasks: 3
  confidence: low   # .planning/estimation-calibration.json tem samples: [] — fator 1.0, sem historico

must_haves:
  truths:
    - "Com DOIS clientes do jogo abertos e a mira configurada, `python -m l2scanner.calibrar --auto` le SO a janela mirada: `capturar_tela` (desktop) nao e chamada nenhuma vez, e a calibracao gravada nao pode misturar barras dos dois clientes porque os pixels do outro cliente nunca entraram na imagem analisada (D-01)."
    - "O nome do personagem mirado vem do `config.toml` e SO de la (ou de `--janela` na linha de comando). Nao existe nome de personagem escrito no fonte: `escolher_janela_do_jogo` recebe o nome como PARAMETRO SEM VALOR PADRAO, entao nao ha onde um padrao se esconder (D-01)."
    - "`--janela \"TITULO\"` vence a chave do `config.toml` sempre que os dois estao presentes (D-01)."
    - "Com mira ativa, o campo `janela` gravado no `calibration.json` E o alvo mirado, e nao um palpite geometrico: `janela_que_contem` nao e consultada nesse caminho. Com os dois clientes SOBREPOSTOS — o cenario que D-04 anuncia como ganho — ela devolveria o cliente de cima, e `party_window_na_janela`, `nome_proprio`, o `origem` de `achar_barra_do_proprio` e o SCANNER EM PRODUCAO herdariam o cliente errado, gravado calado (D-09)."
    - "Mira ativa que nao casa nenhuma janela RECUSA com codigo 1 e LISTA as janelas do jogo abertas agora, com a linha `--janela \"TITULO\"` pronta para copiar — e NUNCA cai para a varredura do desktop, que e exatamente o defeito que a mira existe para fechar (D-02)."
    - "Mira ativa que casa DUAS janelas recusa nomeando as duas, em vez de escolher uma (D-07)."
    - "Sem chave no `config.toml` e sem `--janela`, o comportamento e o de hoje, passo a passo: captura do desktop, `calibrar_automatico`, e o fallback `_tentar_pelas_janelas_do_jogo` quando ele devolve `None` (D-06)."
    - "Com mira ativa, `_tentar_pelas_janelas_do_jogo` NAO roda — ler a janela mirada por dentro ja E o que o fallback fazia, e iterar todas contradiria a mira (D-05)."
    - "`--selecionar` tambem obedece a mira, e a calibracao que sai dele continua em coordenadas de DESKTOP (D-04)."
    - "`--solo` e `--tiat` seguem byte-identicos: os dois retornam antes do ponto onde a mira entra."
    - "A suite inteira deixa de depender do `config.toml` da maquina de quem a roda: `tests/test_calibrar_nao_apaga_mercado.py` neutraliza a mira explicitamente."
    - "O `calibration.json` da raiz do repositorio termina a rodada com o mesmo digest com que comecou, e `VERSAO_DO_ESQUEMA` nao muda."
  artifacts:
    - "l2scanner/config.py com `ler_personagem_do_jogo`"
    - "l2scanner/calibrar.py com `MiraNaoResolvida`, `escolher_janela_do_jogo` (pura) e `capturar_a_janela_mirada`"
    - "config.toml com o bloco `[jogo]` comentado, explicando o PORQUE no estilo do arquivo"
    - "tests/test_mira_da_janela.py"
  key_links:
    - "`capturar_a_janela_mirada` devolve `(pixels, ox, oy)` com `ox, oy = origem_da_janela(hwnd)` — a MESMA assinatura de `capturar_tela()`. E isso que a torna um drop-in no unico ponto de captura de `main()` (calibrar.py:1219) e que faz o resto de `main()` continuar valendo sem edicao: a conta `origem = (jx - ox, jy - oy)`, `party_window_na_janela` e os recortes de assinatura. O contrato ja esta provado em campo por `_tentar_pelas_janelas_do_jogo` (calibrar.py:916), que usa exatamente esse par. A UNICA excecao e `janela_que_contem` — ver o key_link seguinte."
    - "`cal.janela = janela_que_contem(<centro da party window>)` (calibrar.py:~1259) e a unica linha de `main()` que a mira NAO pode deixar como esta. Ela varre `listar_janelas_do_jogo()` e devolve o PRIMEIRO titulo cujo retangulo de desktop contem o ponto (captura_janela.py:151-172) — nao sabe nada da mira. Com mira ativa ela e substituida pelo alvo (D-09); sem mira ela fica intocada, porque ali ela e a ferramenta certa."
    - "`escolher_janela_do_jogo(janelas, pedido, personagem)` e PURA: lista de titulos entra, titulo sai ou excecao sobe. Nenhuma chamada Win32 dentro dela. E o que permite testar as quatro recusas sem o jogo aberto — a suite roda sem cliente nenhum."
    - "`listar_janelas_do_jogo` (captura_janela.py:123) e a UNICA fonte de janelas candidatas: ela ja casa titulo E processo (`l2.bin`), entao uma aba de navegador chamada `XM Essence - Brave` nunca chega a ser mirada."
    - "`cliente.nome_do_personagem(titulo)` (cliente.py:111) e a unica traducao titulo->personagem, a MESMA que `main()` ja usa para `cal.nome_proprio` — chave da config e campo gravado passam a falar o mesmo vocabulario."
    - "`monkeypatch.setattr(l2scanner.calibrar, \"ARQUIVO_CALIBRACAO\", tmp_path / ...)` em TODO caso que chama `main()` — o unico mecanismo que mantem o `calibration.json` real fora do alcance da suite."
---

<objective>
Fazer o `--auto` da calibracao de party MIRAR uma janela especifica do cliente,
em vez de varrer o desktop inteiro.

Purpose: o usuario tem DOIS clientes abertos ao mesmo tempo — confirmado por
`Get-Process` em 2026-08-30: um `L2.bin` com `Faerlina - XM Essence` e outro com
`Yazalaque - XM Essence`. Hoje `main()` captura o desktop inteiro (calibrar.py:
1219) e `calibrar_automatico` (calibrar.py:281) procura faixas vermelhas na
imagem TODA, agrupando-as por espacamento regular. Com duas party windows
visiveis ele pode agrupar barras dos DOIS clientes e deduzir uma geometria que
nao e de nenhum — e como cada passo interno parece bem-sucedido, isso e gravado
CALADO. E a mesma familia do incidente 27x: o perigo nao e o erro que grita, e o
que se certifica sozinho.

O `--janela` ja existe como argumento, mas so o `--tiat` (calibrar.py:1181) e o
`--solo` (calibrar.py:1186) o consomem. O `--auto` o ignora.

Output: uma mira que nasce do `config.toml`, e vencida pelo `--janela`, e que
RECUSA em vez de adivinhar.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/workstreams/mercado/STATE.md
@.claude/CLAUDE.md
</context>

<decisoes>

## Decisoes travadas pelo usuario (2026-08-30) — NAO NEGOCIAVEIS

**D-01 — o personagem padrao vem de chave nova no `config.toml`, NUNCA do fonte.**
`"Yazalaque"` escrito em `l2scanner/` seria constante magica, errada para
qualquer outra pessoa, e o projeto proibe isso explicitamente. O `--janela` na
linha de comando VENCE a config.

**D-02 — janela mirada inexistente: RECUSAR e LISTAR. Falha fechada.**
Jogo fechado, personagem trocado, titulo diferente: recusa, mostra as janelas do
jogo encontradas, e sai com codigo 1. NUNCA cair para a varredura do desktop —
isso reintroduziria exatamente o defeito que a mira fecha.

## Decisoes do planejamento — as quatro perguntas, respondidas por escrito

**D-03 — a chave guarda o NOME DO PERSONAGEM, nao o titulo inteiro.**
Tres razoes, em ordem de peso:
1. **O titulo do cliente nao e estavel dentro da propria sessao.** Jogando ele e
   `Personagem - XM Essence`; na tela de login ele COLAPSA para `XM Essence`
   (`cliente.esta_na_tela_de_login`, cliente.py:92). Uma chave com o titulo
   inteiro casaria nada nesse estado, e a recusa diria "nao achei essa janela"
   quando a verdade e "seu cliente esta no login". Com o nome do personagem a
   ferramenta consegue dizer a verdade: a janela existe, ela e do jogo, e nao
   tem personagem no titulo.
2. **E o que o usuario sabe digitar.** O sufixo ` - XM Essence` e chapa que o
   codigo ja conhece (`cliente.SEPARADOR` / `NOME_DO_CLIENTE`); exigi-lo na mao
   transforma um espaco a mais numa recusa incompreensivel.
3. **`cliente.nome_do_personagem(titulo)` ja e a traducao oficial** e ja e usada
   por `main()` para preencher `cal.nome_proprio` (calibrar.py:1258). Usando a
   mesma funcao, a chave da config e o campo gravado passam a falar o mesmo
   vocabulario, em vez de dois dialetos que divergem na primeira mudanca.

O `--janela` **continua com semantica de TITULO EXATO**, sem mudanca. Nao porque
seja mais bonito, mas porque `--solo` (calibrar.py:844) e `--tiat`
(calibrar.py:985) ja comparam `j == titulo`: dar ao mesmo argumento um segundo
significado dentro da mesma ferramenta seria pior que a assimetria. A recusa
imprime a linha `--janela "TITULO"` pronta para copiar, que e como
`calibrar_so_a_propria_barra` ja resolve isso hoje.

Comparacao **sem diferenciar maiusculas** (`casefold`), depois de `strip`. O
servidor nao permite dois personagens cujos nomes so diferem em caixa, entao
ignorar a caixa nao pode criar uma ambiguidade que ja nao existisse — e recusar
um `yazalaque` digitado em minusculas seria crueldade sem ganho. **Nao** usar
`loot.apelido()`: aquele slug normaliza mais que caixa e faria dois nicks
distintos colapsarem no mesmo alvo.

**D-04 (Pergunta 1) — a mira vale TAMBEM para `--selecionar`.**
A pergunta observa, com razao, que o problema dos dois clientes nao se aplica do
mesmo jeito: o arrasto do mouse ja e uma mira feita pelo olho humano. O que
decide e outra coisa: `main()` tem **um unico ponto de captura** (calibrar.py:
1219), e ele alimenta os dois ramos. Isentar o `--selecionar` significaria criar
um SEGUNDO caminho de captura e um segundo conjunto de regras de coordenada para
uma diferenca que o usuario nao consegue ver. Alem disso a mira melhora o
`--selecionar`: ele passa a mostrar so o cliente que o usuario quis dizer, e
enxerga por baixo de um navegador por cima.

E seguro porque `calibrar_selecionando(pixels, ox, oy)` e honesto quanto a
coordenada — ele repassa `calibrar_automatico(recorte, ox + x, oy + y)`
(calibrar.py:634) — entao com `ox, oy` sendo a origem da janela o resultado sai
em coordenadas de desktop, igualzinho ao que `_tentar_pelas_janelas_do_jogo` ja
produz hoje.

A saida de emergencia continua existindo: `--janela "TITULO"` vence a config, e
a recusa imprime a linha exata.

**D-05 (Pergunta 2) — com mira ativa, `_tentar_pelas_janelas_do_jogo` NAO roda.**
O fallback existe para enxergar por baixo de outra janela por cima. Mas ler a
janela mirada por dentro **ja E** o que o fallback faz — a mira usa o mesmo
`JanelaSource`. O que sobraria do fallback seria so a parte errada dele: iterar
todas as janelas aceitando **a primeira que funcionar**, sem escolher. Isso e o
defeito do desktop em miniatura, e com uma mira declarada seria uma
desobediencia direta. Ele fica vivo **so no caminho sem mira**, onde nao ha
ordem para contrariar.

**D-06 (Pergunta 3) — chave ausente: exatamente o comportamento de hoje.**
Instalacao nova, usuario que nunca configurou, ou quem tem um cliente so: sem
chave e sem `--janela` **nao ha mira**, e o fluxo e o de hoje passo a passo —
desktop, `calibrar_automatico`, fallback. Sem mira nao ha o que recusar; a
recusa fechada de D-02 so existe quando alguem PEDIU um alvo. Quebrar o `--auto`
de quem tem um cliente so seria regressao, e nao rigor.

**D-07 (Pergunta 4) — duas janelas casando a mesma mira: RECUSA nomeando as duas.**
A doutrina da casa e recusar e nomear, e aqui ela e literal: escolher uma das
duas e reinventar o `_tentar_pelas_janelas_do_jogo` ("a primeira que funcionar")
dentro da propria mira. Vale para os dois eixos:
- dois titulos com o mesmo personagem;
- **dois clientes na tela de login**, que e o caso real e nada teorico: os dois
  tem o titulo `XM Essence` identico, entao ate um `--janela "XM Essence"` de
  titulo exato casa duas janelas. Recusa igual.

**D-08 — precedencia `config.local.toml` > `config.toml`, avisando alto quando os dois tem a chave.**
Mesmo idioma de `ler_membros` (config.py:293), pelo mesmo motivo escrito la: uma
chave que nao faz nada e invisivel; uma chave que nao faz nada e nao avisa e uma
armadilha — o usuario reedita a noite inteira o arquivo errado. O usuario ja tem
o habito do `config.local.toml` (e onde moram os `[[membro]]`), entao ignorar a
chave la em silencio e um modo de falha provavel, nao hipotetico.

**D-09 — com mira ativa, `cal.janela` recebe o ALVO. `janela_que_contem` nao e consultada, e nao vira aviso tambem.**
`main()` faz hoje `cal.janela = janela_que_contem(<centro da party window>)`
(calibrar.py:~1259), consumindo `captura_janela.py:151-172` — que varre
`listar_janelas_do_jogo()` e devolve **o primeiro titulo cujo retangulo de
desktop contem o ponto**. Ela nao sabe nada da mira.

O cenario em que ela erra e **exatamente o que D-04 anuncia como ganho**: dois
clientes SOBREPOSTOS. A party window lida de dentro da janela A tem coordenadas
de desktop que caem dentro do retangulo de B, entao `cal.janela = B` — e dali
para baixo `party_window_na_janela`, o `origem` de `achar_barra_do_proprio`,
`nome_proprio` (derivado de `cal.janela.split(" - ")`) e **o scanner em
producao**, que segue `cal.janela`, todos apontam para o cliente errado. Gravado
calado. E o mesmo modo de falha que esta tarefa fecha, deslocado do pixel para o
campo — o primo dele ja esta descrito no comentario logo acima daquela linha ("o
canto caiu 12 px dentro da janela da Faerlina").

**E por que nem como AVISO:** com a mira ativa, os pixels vieram do frame de A
**por construcao**. A party window achada esta dentro do conteudo de A; ela nao
pode pertencer a B. A sobreposicao em coordenadas de desktop e artefato puro de
empilhamento de janelas, entao uma discordancia de `janela_que_contem` carrega
**zero informacao** sobre acerto — ela e GARANTIDA sempre que A estiver coberta,
que e justamente o caso suportado. Um aviso que dispara sempre no cenario
suportado nao informa: ensina o usuario a ignorar avisos.

Sem mira, `janela_que_contem` fica **intocada**: ali ninguem declarou alvo, e
adivinhar pela geometria e a melhor informacao existente.

</decisoes>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: A mira, de ponta a ponta — do config.toml ate o frame de UMA janela</name>

  <files>l2scanner/config.py, l2scanner/calibrar.py, tests/test_mira_da_janela.py</files>

  <read_first>
    - `l2scanner/config.py:141-165` (`ler_agenda`) — o idioma de leitura do `config.toml`: `caminho or ARQUIVO_CONFIG`, ausencia nao e erro, TOML quebrado e `AgendaInvalida` citando o nome do arquivo.
    - `l2scanner/config.py:293-345` (`ler_membros`) — a docstring que EXPLICA por que `AgendaInvalida` e reusada em vez de excecao propria, e a precedencia entre os dois arquivos com aviso quando ambos tem bloco (D-08). Copiar esse formato.
    - `l2scanner/calibrar.py:916-965` (`_tentar_pelas_janelas_do_jogo`) — o caminho completo `achar_janela` -> `origem_da_janela` -> `JanelaSource(titulo, Regiao(ox, oy, 1, 1))` -> `sleep(0.6)` -> `capturar_completo()` -> `fonte.fechar()` no `finally`. E o idioma a copiar, incluindo a razao escrita do sleep.
    - `l2scanner/calibrar.py:1215-1235` (`main`) — o unico ponto de captura e o ramo `--selecionar`/`--auto`.
    - `l2scanner/calibrar.py:1250-1275` (`main`) — o bloco `cal.janela = janela_que_contem(...)`, a conta `origem = (jx - ox, jy - oy)` e `nome_proprio`. E o trecho que D-09 altera.
    - `l2scanner/captura_janela.py:151-172` (`janela_que_contem`) — devolve o PRIMEIRO titulo cujo retangulo contem o ponto. Ler para ver que ela nao tem como saber de mira nenhuma.
    - `l2scanner/captura_janela.py:123-148` (`listar_janelas_do_jogo`) — casa titulo E processo, com a razao na docstring.
    - `l2scanner/cliente.py:92-115` — `esta_na_tela_de_login` e `nome_do_personagem`.
    - `tests/test_calibrar_nao_apaga_mercado.py:259-290` (`_dirigir`) e `:390-406` (`_JanelaFalsa`) — como se dirige `main()` sem jogo aberto e como se falsifica `JanelaSource`.
  </read_first>

  <behavior>
    - `ler_personagem_do_jogo(caminho=<toml com [jogo] personagem = "Alfa">)` devolve `"Alfa"`.
    - `ler_personagem_do_jogo(caminho=<toml sem a secao>)` devolve `None`; arquivo inexistente tambem devolve `None`.
    - `escolher_janela_do_jogo(["Alfa - XM Essence", "Beta - XM Essence"], None, "Alfa")` devolve `"Alfa - XM Essence"`.
    - `escolher_janela_do_jogo([...], None, "alfa")` devolve a mesma janela — a caixa nao decide (D-03).
    - `escolher_janela_do_jogo([...], None, None)` devolve `None`: sem mira, sem recusa (D-06).
    - Dirigindo `main()` com `--auto`, duas janelas abertas e a chave apontando para uma delas: `JanelaSource` e construida com o titulo da janela MIRADA, `capturar_tela` nao e chamada NENHUMA vez, e `_tentar_pelas_janelas_do_jogo` nao e chamada NENHUMA vez (D-05).
    - O console diz qual janela mirou E de onde veio a mira (`--janela` ou `config.toml`) — com dois clientes abertos, saber POR QUE aquela foi escolhida e o que permite ao usuario perceber um alvo errado antes de gravar.
    - Dirigindo `main()` com a mira em `Alfa` e `janela_que_contem` FALSIFICADO para devolver `"Beta - XM Essence"` (o cliente de cima, que e o que ela devolveria de verdade com as janelas sobrepostas): o `calibration.json` gravado tem `janela == "Alfa - XM Essence"`, e `nome_proprio == "Alfa"` (D-09).
    - Sem mira, `janela_que_contem` continua sendo quem decide `cal.janela` — o caso ja coberto por `tests/test_calibrar_nao_apaga_mercado.py` nao muda de resposta (D-09).
  </behavior>

  <action>
    Em `l2scanner/config.py`, criar `ler_personagem_do_jogo(caminho: Path | None = None, caminho_local: Path | None = None) -> str | None`, lendo `[jogo] personagem` — implementa D-01. Seguir `ler_membros` (config.py:293) linha a linha na forma: os dois `None` significam "use os dois arquivos padrao com precedencia"; um `caminho` explicito le SO aquele arquivo, sem procurar vizinho, porque e disso que depende o guarda que a Task 3 escreve sobre o arquivo do repositorio. `config.local.toml` vence o `config.toml`; quando os DOIS trazem a chave, emitir `log.warning` nomeando o vencedor e dizendo que o outro esta sendo ignorado (D-08). Ausencia de arquivo, de secao ou de chave devolve `None` — nao e erro (D-06). TOML mal formado levanta `AgendaInvalida` citando o nome do arquivo, reusando a excecao pelo motivo ja escrito na docstring de `ler_membros`; um valor que nao seja texto (lista, numero) levanta `AgendaInvalida` dizendo o tipo que veio e mostrando a forma certa, no mesmo espirito da recusa de `ler_watchlist` (calibrar_mercado.py:1120) para `watchlist` string. Devolver o valor com `strip` aplicado, e tratar texto so de espacos como ausencia.

    Em `l2scanner/calibrar.py`, criar a excecao `MiraNaoResolvida(Exception)` com docstring dizendo que ela carrega a mensagem PRONTA para o usuario, e a funcao PURA `escolher_janela_do_jogo(janelas: list[str], pedido: str | None, personagem: str | None) -> str | None`. Nenhuma chamada Win32 dentro dela: a lista de titulos entra por parametro. `personagem` e `pedido` sao parametros SEM valor padrao — e o que torna estruturalmente impossivel um nome de personagem se esconder como padrao no fonte (D-01). Regra: `pedido` e `personagem` ambos ausentes devolve `None` (D-06); `pedido` presente casa titulo EXATO e vence a config (D-01, D-03); senao, casa `cliente.nome_do_personagem(titulo)` contra `personagem` por `casefold()` depois de `strip()`. Zero ou dois ou mais casamentos levantam `MiraNaoResolvida` — as mensagens sao trabalho da Task 2; aqui basta que a excecao suba com o alvo pedido citado.

    Ainda em `calibrar.py`, criar `capturar_a_janela_mirada(titulo: str) -> tuple[np.ndarray, int, int]`, copiando o idioma de `_tentar_pelas_janelas_do_jogo` (calibrar.py:930-950): `achar_janela` -> `origem_da_janela` -> `JanelaSource(titulo, Regiao(ox, oy, 1, 1))` -> `time.sleep(0.6)` (mantendo a razao escrita: deixa chegar um frame de verdade) -> `capturar_completo()` -> `fonte.fechar()` num `finally`. Devolver `(pixels, ox, oy)` com `ox, oy = origem_da_janela(hwnd)` — a MESMA assinatura de `capturar_tela()`, e a docstring precisa dizer que e por isso que ela e um drop-in e que todo o resto de `main()` continua valendo sem edicao. Frame ausente ou vazio levanta `MiraNaoResolvida` explicando janela minimizada, do jeito que `JanelaSource._esperar_primeiro_frame` (captura_janela.py:299) ja explica.

    Em `main()`, antes da linha que hoje imprime a captura da tela (calibrar.py:1219) e DEPOIS dos retornos de `--tiat` e `--solo` — que ficam intocados —, resolver o alvo e capturar dentro de **UM UNICO `try`** que captura `MiraNaoResolvida` e `AgendaInvalida`, imprime a mensagem sem traceback e devolve `1`. O `try` precisa cobrir a resolucao E a captura: `capturar_a_janela_mirada` tambem levanta `MiraNaoResolvida` (janela minimizada), e deixa-la fora do `try` faria a mensagem mais provavel de todas — a que o usuario ve quando esqueceu o cliente minimizado — sair como traceback.

    Dentro dele: ler o personagem da config; **so enumerar janelas quando alguem pediu alvo** — `if args.janela or personagem:` antes de chamar `listar_janelas_do_jogo()`. Sem esse curto-circuito, o caminho SEM mira (D-06) passaria a fazer um `EnumWindows` real que hoje nao acontece naquele ponto, mudando o comportamento de quem nao pediu nada — e prendendo a suite as janelas da maquina. A regra "ambos ausentes devolve `None`" continua dentro de `escolher_janela_do_jogo` como contrato para quem a chama direto, inclusive o teste; ela so deixa de ser o caminho por onde `main()` passa.

    Com alvo: imprimir a linha que nomeia a janela mirada e a origem da mira, e capturar por `capturar_a_janela_mirada(alvo)`. Sem alvo: `capturar_tela()`, exatamente como hoje. No ramo `--auto`, so chamar `_tentar_pelas_janelas_do_jogo` quando NAO ha alvo (D-05) — e escrever no codigo, em comentario curto, que com mira a leitura por dentro ja aconteceu. `--selecionar` recebe `pixels, ox, oy` como sempre recebeu, sem ramo proprio (D-04).

    Ainda em `main()`, no bloco `cal.janela = janela_que_contem(...)` (calibrar.py:~1259): com alvo, atribuir `cal.janela = alvo` e **nao chamar** `janela_que_contem`; sem alvo, deixar a linha exatamente como esta (D-09). O comentario que ja mora ali explica por que o centro e melhor que o canto — acrescentar abaixo dele, em prosa curta, a razao de D-09: com a mira os pixels vieram do frame daquela janela POR CONSTRUCAO, entao a dona e conhecida com certeza, e um palpite geometrico so pode subtrair certeza — com os dois clientes sobrepostos ele devolveria o de cima. Conferir por leitura que `nome_proprio` e `party_window_na_janela`, que derivam de `cal.janela` logo abaixo, herdam o alvo sem edicao propria.

    Criar `tests/test_mira_da_janela.py` com os casos do bloco `behavior`. Docstring do arquivo registrando o incidente que ele prende: dois `L2.bin` abertos, `calibrar_automatico` agrupando barras dos dois e gravando calado. Fixtures usam nomes NEUTROS (`Alfa`, `Beta`) e nunca o roster real — o teste nao pode depender de quem o usuario e. Todo caso que chama `main()` monkeypatcha, no namespace `l2scanner.calibrar` (que e onde os nomes foram importados, calibrar.py:43 — patchar em `l2scanner.captura_janela` nao alcanca): `ARQUIVO_CALIBRACAO` para dentro de `tmp_path`; `JanelaSource` para uma dupla do `_JanelaFalsa`; `listar_janelas_do_jogo` para a lista de titulos do caso; **`achar_janela`** para um hwnd inventado; **`origem_da_janela`** para o par `(ox, oy)` do caso; e `janela_que_contem`. Os dois em negrito nao sao opcionais: `capturar_a_janela_mirada` chama os dois de verdade, e sem eles `achar_janela` levanta `JanelaNaoEncontrada` (captura_janela.py:85) numa maquina sem o jogo aberto — o criterio "a suite roda sem jogo aberto" nao se cumpriria, e a falha apareceria longe da causa. `origem_da_janela` falsificado tambem e o que da ao teste um `(ox, oy)` ESPERADO para afirmar. A dupla de `JanelaSource` precisa REGISTRAR o titulo com que foi construida — e essa gravacao que prova qual janela foi mirada.
  </action>

  <verify>
    <automated>python -m pytest tests/test_mira_da_janela.py -x -q</automated>
  </verify>

  <acceptance_criteria>
    - `python -m pytest tests/test_mira_da_janela.py -q` passa.
    - Existe um caso que afirma, dirigindo `main()` com duas janelas na lista, que a dupla de `JanelaSource` registrou o titulo da janela MIRADA — e nao o da outra.
    - Existe um caso que afirma que `capturar_tela` nao foi chamada nesse fluxo (contador ou `pytest.fail` dentro da dupla).
    - `inspect.signature(l2scanner.calibrar.escolher_janela_do_jogo)` mostra `personagem` e `pedido` sem valor padrao — a prova estrutural de D-01.
    - Existe um caso em que `janela_que_contem` esta falsificado para devolver a OUTRA janela e o `calibration.json` gravado tem `janela` igual ao alvo mirado — a prova de D-09. O caso falha no codigo de hoje.
    - Nenhum caso de `main()` com mira depende de `achar_janela` ou `origem_da_janela` reais: rodar a suite com o jogo FECHADO passa.
    - `git diff --stat` nao toca `l2scanner/rastreador.py` nem `l2scanner/visao.py`.
    - `calibration.json` da raiz nao aparece no `git status` nem tem o mtime alterado.
  </acceptance_criteria>

  <done>Com a chave configurada, `--auto` le exclusivamente o frame da janela mirada; sem chave e sem `--janela`, nada muda. Provado por teste que roda sem o jogo aberto.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Falha fechada — as quatro recusas, a precedencia, e a suite deixando de depender da maquina</name>

  <files>l2scanner/calibrar.py, tests/test_mira_da_janela.py, tests/test_calibrar_nao_apaga_mercado.py</files>

  <read_first>
    - `l2scanner/calibrar.py:842-855` (`calibrar_so_a_propria_barra`) — a recusa que ja existe no projeto para "ha mais de uma janela aberta", imprimindo `--janela "TITULO"` linha a linha. E o formato a repetir.
    - `l2scanner/captura_janela.py:77-88` (`achar_janela`) — a mensagem que ja lista as janelas do jogo e diz "o jogo esta aberto?" quando a lista esta vazia.
    - `l2scanner/cliente.py:92-110` (`esta_na_tela_de_login`) — a razao pela qual a comparacao e exata contra o nome do cliente.
    - `tests/test_calibrar_nao_apaga_mercado.py:1-33` (docstring) e `:259-290` (`_dirigir`) — a disciplina inegociavel do arquivo e o helper que precisa ganhar a neutralizacao da mira.
  </read_first>

  <behavior>
    - Mira por personagem que nao casa nenhuma das janelas abertas: `main()` devolve `1`, a saida nomeia o personagem pedido, LISTA os titulos das janelas do jogo abertas e imprime para cada um a linha `--janela "TITULO"` (D-02).
    - Nenhuma janela do jogo aberta com a mira ativa: `main()` devolve `1` e a mensagem pergunta se o jogo esta aberto, em vez de listar o vazio (D-02).
    - Em QUALQUER recusa, `capturar_tela` nao e chamada e nada e gravado em disco — o arquivo apontado por `ARQUIVO_CALIBRACAO` fica byte a byte igual (D-02).
    - Duas janelas casando o mesmo personagem: recusa nomeando AS DUAS (D-07).
    - Dois clientes na tela de login (dois titulos `XM Essence` identicos) com `--janela "XM Essence"`: recusa por ambiguidade, e nao "primeira que funcionar" (D-07).
    - Ha janela do jogo aberta mas nenhuma tem personagem no titulo: a recusa DIZ que a janela esta na tela de login, em vez de dizer so "nao achei" (D-03).
    - `--janela "Beta - XM Essence"` com a config apontando `Alfa`: a janela mirada e a do `--janela` (D-01).
    - Sem chave e sem `--janela`, com duas janelas abertas: `main()` NAO recusa, captura o desktop, e `_tentar_pelas_janelas_do_jogo` continua sendo chamada quando `calibrar_automatico` devolve `None` (D-06, D-05).
    - `--selecionar` com mira ativa recebe os pixels da janela mirada e `(ox, oy)` iguais ao que `origem_da_janela` falsificado devolveu; a `Calibracao` que sai continua em coordenadas de desktop (D-04).
    - Janela mirada que nao entrega frame (minimizada): `main()` devolve `1` com a mensagem explicando janela minimizada, e SEM traceback — a excecao vem da captura, nao da resolucao (W-2).
    - `config.local.toml` com a chave vence o `config.toml` com a chave, e o aviso nomeia o vencedor (D-08).
  </behavior>

  <action>
    Escrever as mensagens de `MiraNaoResolvida` em `escolher_janela_do_jogo`, uma por caso, no formato que `calibrar_so_a_propria_barra` (calibrar.py:848-852) ja usa: frase curta dizendo o que foi pedido, depois a lista de janelas com a linha de argumento pronta para copiar. Quatro casos distintos, cada um com sua frase — implementa D-02 e D-07:
    (a) nenhuma janela do jogo na lista: perguntar se o jogo esta aberto, sem listar vazio;
    (b) ha janelas, nenhuma casa o personagem pedido: nomear o personagem e listar as janelas; quando alguma delas satisfizer `cliente.esta_na_tela_de_login`, acrescentar a linha dizendo que aquela esta na tela de login e por isso nao tem personagem no titulo (D-03);
    (c) `--janela` com titulo que nao existe na lista: mesma listagem, frase citando o titulo pedido;
    (d) duas ou mais casando: dizer que nao da para escolher, listar as CASADAS e mandar desambiguar com `--janela` (D-07).
    Nenhuma dessas mensagens sugere tentar o desktop, e o codigo nao tem caminho para isso — a recusa retorna `1` de `main()`.

    Verificar por leitura que `main()` nao grava nada antes do ponto de captura, e que o `return 1` da recusa acontece antes de qualquer `salvar` — a recusa nao pode passar perto de `fundir_com_a_calibracao_em_disco` nem do `cal.salvar` final (calibrar.py:1329).

    Em `tests/test_calibrar_nao_apaga_mercado.py`, acrescentar ao helper `_dirigir` (linha 259) DUAS neutralizacoes, com comentario no mesmo tom da linha do `ARQUIVO_CALIBRACAO` logo acima. O seam tem de ser nomeado pelo lugar onde o nome VIVE: se `calibrar.py` fizer `from .config import ler_personagem_do_jogo`, o alvo e `l2scanner.calibrar.ler_personagem_do_jogo`, e patchar `l2scanner.config.ler_personagem_do_jogo` nao alcanca nada — conferir a forma do import escrito na Task 1 e patchar a que existir.
    (1) a leitura do personagem devolvendo `None`: sem ela, no dia em que o usuario preencher a chave no `config.toml` da maquina dele, esta suite passa a tentar abrir uma janela de jogo de verdade e quebra por um motivo que nao tem nada a ver com o que ela afirma. Um teste que le a configuracao da maquina de quem o roda nao esta afirmando nada.
    (2) `l2scanner.calibrar.listar_janelas_do_jogo` devolvendo `[]`: com o curto-circuito da Task 1 ela nem chega a ser chamada nesse caminho, e e por isso mesmo que ela entra — como cinto que segura o dia em que alguem tirar o curto-circuito sem perceber que estava prendendo a suite ao `EnumWindows` da maquina.

    Acrescentar os casos do bloco `behavior` a `tests/test_mira_da_janela.py`, com nomes neutros (`Alfa`, `Beta`). O caso da precedencia D-08 escreve dois arquivos TOML em `tmp_path` e chama `ler_personagem_do_jogo` com os dois caminhos explicitos — nunca os padroes, para que o teste jamais toque os arquivos reais do repositorio. O caso do `--selecionar` monkeypatcha `calibrar_selecionando` para capturar os `(pixels, ox, oy)` recebidos e afirma que `ox, oy` sao a origem da janela mirada.
  </action>

  <verify>
    <automated>python -m pytest tests/test_mira_da_janela.py tests/test_calibrar_nao_apaga_mercado.py -q</automated>
  </verify>

  <acceptance_criteria>
    - `python -m pytest tests/test_mira_da_janela.py tests/test_calibrar_nao_apaga_mercado.py -q` passa.
    - Cada uma das quatro recusas (a, b, c, d) tem um caso proprio que inspeciona a saida com `capsys` e afirma que o titulo relevante aparece nela.
    - Existe um caso que afirma que, apos uma recusa, o arquivo apontado por `ARQUIVO_CALIBRACAO` tem exatamente o mesmo conteudo que tinha antes.
    - `_dirigir` em `tests/test_calibrar_nao_apaga_mercado.py` neutraliza a mira, e o comentario explica que isso mantem a suite independente do `config.toml` da maquina.
    - Os 6 casos que ja existiam em `tests/test_calibrar_nao_apaga_mercado.py` continuam passando sem alteracao de logica — so o helper mudou.
  </acceptance_criteria>

  <done>Toda mira que nao resolve para exatamente uma janela recusa com codigo 1, nomeia o que encontrou, e nao grava nada. Nenhum caminho leva de volta a varredura do desktop.</done>
</task>

<task type="auto">
  <name>Task 3: O que o usuario le — o bloco no config.toml, e o guarda contra a chave que nao existe</name>

  <files>config.toml, l2scanner/calibrar.py, tests/test_mira_da_janela.py</files>

  <read_first>
    - `config.toml:134-160` — o bloco da watchlist do mercado: comentado, com o PORQUE antes do COMO, e o exemplo desligado de proposito para o arquivo do repositorio nao carregar dado de ninguem. E o modelo exato a seguir.
    - `config.toml:1-9` — o cabecalho que explica a diferenca entre este arquivo e o `calibration.json`.
    - `config.toml:108-121` — a explicacao de por que dado pessoal vai para `config.local.toml`, e a nota de que o arquivo do repositorio continua versionado por causa da agenda.
    - `l2scanner/calibrar.py:1-18` — a docstring do modulo, que hoje descreve `--auto` como "procura a janela do jogo, varre a tela".
    - `tests/test_agenda.py` — o precedente de teste que le o `config.toml` DO REPOSITORIO.
  </read_first>

  <action>
    Escrever no `config.toml` a secao `[jogo]` COMENTADA, no estilo do bloco da watchlist: primeiro o problema (dois clientes abertos ao mesmo tempo fazem a calibracao automatica juntar barras dos dois e deduzir uma geometria que nao e de nenhum, e isso e gravado sem reclamar), depois a chave, depois o que acontece sem ela (nada muda: com um cliente so o `--auto` funciona como sempre funcionou — D-06), depois o que acontece quando ela aponta para uma janela que nao existe (a ferramenta recusa e lista as janelas abertas, em vez de varrer o desktop — D-02), e por fim que `--janela "TITULO"` na linha de comando vence esta chave (D-01). Dizer tambem que se escreve o NOME DO PERSONAGEM e nao o titulo inteiro, e por que (o titulo colapsa na tela de login — D-03), e que esta chave dirige a CALIBRACAO: o scanner em si aprende a janela pelo `calibration.json` que a calibracao grava. Registrar que este dado nao e segredo — e nome publico dentro do jogo — e por isso pode morar aqui; e que quem preferir pode escrever no `config.local.toml`, que vence (D-08). Manter o exemplo COMENTADO, pelo mesmo motivo escrito no bloco dos `[[membro]]`: o arquivo do repositorio nao carrega o personagem de ninguem.

    Atualizar a docstring do modulo `l2scanner/calibrar.py` (linhas 1-18) para descrever o `--auto` como ele passa a ser: com a mira configurada le so a janela mirada; sem mira, varre a tela como antes. Atualizar o texto de ajuda do argumento `--janela` (calibrar.py:1163) para dizer que ele vale tambem para o `--auto` e que vence a chave do `config.toml`.

    Para que o guarda de deriva abaixo tenha MECANISMO e nao so intencao, extrair em `l2scanner/config.py` duas constantes de modulo — o nome da secao e o nome da chave — e fazer `ler_personagem_do_jogo` indexar o TOML por elas, em vez de repetir literais no corpo. E o unico jeito de o teste comparar o documento com o leitor sem que os dois possam divergir: `tomllib` nao le comentario, entao um assert sobre "o que o comentario diz" so tem como se ancorar no TEXTO do arquivo.

    Acrescentar a `tests/test_mira_da_janela.py` um guarda de DERIVA lendo o `config.toml` DO REPOSITORIO — mesmo precedente de `tests/test_agenda.py`, e pelo mesmo tipo de razao: uma chave documentada no arquivo com um nome que o codigo nao le deixa o usuario reeditando para sempre uma linha que nao faz nada, e nada no mundo o avisa. Duas afirmacoes, cada uma com seu mecanismo:
    (1) DERIVA: ler o TEXTO do `config.toml` do repositorio e afirmar que o cabecalho de secao montado a partir da constante de secao aparece nele, e que uma linha de exemplo montada a partir da constante de chave aparece nele. As duas montadas EM TEMPO DE TESTE a partir das constantes que o leitor usa — renomear qualquer um dos dois lados quebra o guarda, que e o ponto.
    (2) O ARQUIVO DO REPOSITORIO NAO CARREGA O PERSONAGEM DE NINGUEM: chamar `ler_personagem_do_jogo` com o caminho explicito do `config.toml` do repositorio e afirmar que devolve `None`. Isso prova que o bloco esta comentado sem depender de casar texto — se alguem descomentar e commitar o proprio personagem, o guarda cai.
  </action>

  <verify>
    <automated>python -m pytest tests/test_mira_da_janela.py -q && python -m pytest tests/ -q</automated>
  </verify>

  <acceptance_criteria>
    - `python -m pytest tests/ -q` volta ao verde do baseline mais os casos novos: 1830 passed + os novos, 2 skipped. Aborto por `KeyboardInterrupt` vindo de `tests/test_agenda.py` e o flake conhecido — rodar de novo, aborto nao e falha.
    - O guarda de deriva falha se alguem renomear a secao ou a chave num dos dois lados.
    - `ler_personagem_do_jogo(<config.toml do repositorio>)` devolve `None`.
    - `git diff config.toml` mostra so acrescimo de bloco comentado; nenhuma linha existente do arquivo mudou.
    - Nenhuma dependencia nova em `pyproject.toml` nem em `requirements*.txt` (FIRE-01).
    - `VERSAO_DO_ESQUEMA` inalterada; `l2scanner/calibracao.py` fora do diff.
  </acceptance_criteria>

  <done>O usuario consegue ligar a mira lendo so o `config.toml`, e a suite prova que o nome da chave documentada e o nome da chave lida.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `config.toml` / `config.local.toml` -> ferramenta de calibracao | texto escrito a mao pelo usuario, versionado e fotografado quando ele pede ajuda |
| titulos de janela de OUTROS processos -> `listar_janelas_do_jogo` | qualquer programa da maquina pode nomear a propria janela `XM Essence` |
| ferramenta -> `calibration.json` | escrita destrutiva num arquivo gitignored, sem `git checkout` para trazer de volta |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-BVO-01 | Spoofing | `escolher_janela_do_jogo` / `listar_janelas_do_jogo` | medium | mitigate | A lista de candidatas vem SO de `listar_janelas_do_jogo` (captura_janela.py:123), que casa titulo E processo `l2.bin`. Uma aba `XM Essence - Brave` nunca chega a ser mirada. Task 1 nao pode montar uma segunda enumeracao de janelas. |
| T-BVO-02 | Information disclosure | bloco `[jogo]` no `config.toml` versionado | low | mitigate | A chave guarda so o nome do personagem — publico dentro do jogo, nao credencial. O bloco entra COMENTADO (Task 3) e um teste afirma que o arquivo do repositorio nao traz a chave ativa. Nada de token, telefone ou caminho de maquina entra ali. |
| T-BVO-03 | Tampering | mira que resolve para o cliente errado | high | mitigate | Falha fechada (D-02, D-07): zero ou duas janelas casando RECUSA com codigo 1 e nomeia o que encontrou; nao ha caminho de volta ao desktop. O console nomeia a janela mirada E a origem da mira antes de calibrar, entao o usuario ve o alvo errado antes de gravar. Task 2 afirma cada recusa com `capsys`. |
| T-BVO-06 | Tampering | `cal.janela` decidido por `janela_que_contem` com os clientes sobrepostos | high | mitigate | Com mira ativa o campo recebe o ALVO e o palpite geometrico nao e consultado (D-09). Sem isso o cliente de cima seria gravado e herdado por `party_window_na_janela`, `nome_proprio`, o `origem` de `achar_barra_do_proprio` e pelo SCANNER EM PRODUCAO — calado, e justamente no cenario de janelas cobertas que D-04 anuncia como ganho. Task 1 afirma com `janela_que_contem` falsificado devolvendo a outra janela. |
| T-BVO-04 | Tampering | `calibration.json` (13 moldes de glifo, 3 ancoras, grade) | high | mitigate | `fundir_com_a_calibracao_em_disco` (calibrar.py:1083, commit `0c9038c`) fica INTOCADA e o seam continua sendo o unico ponto antes do `salvar`. Todo caso de teste que chama `main()` monkeypatcha `ARQUIVO_CALIBRACAO` para `tmp_path`. Recusa nao grava nada (Task 2). Acceptance de Task 1 confere o mtime do arquivo real. |
| T-BVO-05 | Denial of service | teste lendo o `config.toml` da maquina | medium | mitigate | `_dirigir` neutraliza a mira (Task 2) e o guarda de deriva usa caminho explicito. Sem isso, no dia em que o usuario preencher a chave, a suite passa a exigir jogo aberto e quebra longe da causa. |
| T-BVO-SC | Tampering | instalacao de pacote (npm/pip/cargo) | n/a | accept | Nenhum pacote e instalado neste plano — FIRE-01 proibe dependencia nova, e tudo usado (`tomllib`, `ctypes`, `numpy`, `cv2`) ja esta no projeto. O portao de legitimidade nao tem o que examinar; a acceptance de Task 3 afirma que os arquivos de dependencia nao mudaram. |
</threat_model>

<verification>
1. `python -m pytest tests/test_mira_da_janela.py -q` — os casos novos passam.
2. `python -m pytest tests/ -q` — baseline (1830 passed, 2 skipped) mais os novos, sem regressao. Aborto por `KeyboardInterrupt` de `tests/test_agenda.py` e flake conhecido: rodar de novo.
3. `git status --short` nao lista `calibration.json`, e o digest do arquivo e o mesmo do inicio da rodada.
4. `git diff --stat` toca apenas: `l2scanner/config.py`, `l2scanner/calibrar.py`, `config.toml`, `tests/test_mira_da_janela.py`, `tests/test_calibrar_nao_apaga_mercado.py`.
5. Conferencia manual pelo usuario, com os DOIS clientes abertos (unico passo que exige o jogo): preencher a chave, rodar `calibrar.bat`, confirmar que o console nomeia a janela certa e que a imagem de conferencia mostra a party window do cliente pretendido.
</verification>

<success_criteria>
- Com a chave configurada e dois clientes abertos, `--auto` analisa pixels de UMA janela so.
- Mira que nao resolve para exatamente uma janela recusa, nomeia, e nao grava.
- Sem chave e sem `--janela`, o comportamento de hoje esta intacto, fallback incluido.
- Nenhum nome de personagem no fonte; nenhuma dependencia nova; `VERSAO_DO_ESQUEMA` inalterada.
- `rastreador.py`, `visao.py` e `fundir_com_a_calibracao_em_disco` fora do diff.
</success_criteria>

<artifacts>
## Artifacts this phase produces

| Artifact | Kind | Produced by |
|----------|------|-------------|
| `l2scanner/config.py` — `ler_personagem_do_jogo` | codigo | Task 1 |
| `l2scanner/calibrar.py` — `MiraNaoResolvida`, `escolher_janela_do_jogo`, `capturar_a_janela_mirada`, fiacao em `main()` | codigo | Tasks 1, 2 |
| `l2scanner/calibrar.py` — docstring do modulo e ajuda do `--janela` | documentacao | Task 3 |
| `config.toml` — bloco `[jogo]` comentado | configuracao documentada | Task 3 |
| `tests/test_mira_da_janela.py` | teste | Tasks 1, 2, 3 |
| `tests/test_calibrar_nao_apaga_mercado.py` — `_dirigir` neutralizando a mira | teste | Task 2 |
</artifacts>

<output>
Create `.planning/workstreams/mercado/quick/260830-bvo-o-auto-da-calibracao-mira-uma-janela-nao/260830-bvo-SUMMARY.md` when done
</output>
