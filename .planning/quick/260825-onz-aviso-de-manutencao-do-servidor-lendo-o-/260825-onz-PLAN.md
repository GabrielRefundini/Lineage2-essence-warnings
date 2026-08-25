---
phase: quick-260825-onz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/manutencao.py
  - l2scanner/ocr.py
  - l2scanner/sessao.py
  - l2scanner/calibracao.py
  - l2scanner/__main__.py
  - requirements.txt
  - vigiar-party.bat
  - tests/test_manutencao.py
  - tests/test_ocr.py
  - tests/test_sessao.py
autonomous: true
requirements: [QUICK-260825-onz]

estimate:
  tokens: 96000
  raw_tokens: 48000
  tasks: 4
  confidence: low

must_haves:
  truths:
    - "Quando o banner de manutencao aparece na tela, o grupo recebe no WhatsApp UM aviso dizendo o tempo COMO ESTA NA TELA e a que horas o servidor cai (D-01, D-04, GOAL-01)."
    - "Quando falta ate 5 minutos para a manutencao, o grupo recebe o SEGUNDO aviso — e ele sai do RELOGIO ANCORADO, nao da tela (D-04, D-10, GOAL-02)."
    - "O aviso de 5 minutos sai mesmo que o banner tenha sumido, o jogo esteja coberto ou o OCR passe a devolver None depois da ancoragem (D-10). Robustez contra cegueira e o motivo inteiro de a ancora existir."
    - "Uma leitura discrepante NAO anuncia: com 40, depois 4, depois 40 minutos, nada sai. Sao precisas DUAS leituras cujos momentos implicados batam dentro da tolerancia (D-05)."
    - "Texto que nao e o banner nunca vira manutencao. `You cannot use this item because the server will restart in a few minutes` — frase real dos prints do usuario — NAO e banner (D-03)."
    - "O typo do jogo (`Maintence`) e a grafia correta (`Maintenance`) sao aceitos igualmente, em qualquer caixa (D-03)."
    - "As confusoes de OCR (O->0, l/I->1, S->5) sao normalizadas SO em token que ja tem digito de verdade — `seconds` sobrevive intacto (D-03)."
    - "Cada aviso sai UMA vez so, inclusive com as DUAS instancias do usuario competindo pelo mesmo marcador em `.agenda/` (D-09)."
    - "O marcador tem a DATA NA FRENTE (`2026-08-25_manutencao-1435_anunciada`), entao o `podar()` de 3 dias o remove — sem o prefixo a pasta cresceria para sempre (D-09)."
    - "A ancora EXPIRA depois que o momento passa (com folga curta) e nao reavisa nem carrega ancora velha (D-10)."
    - "Sem as bindings do WinRT ou sem pacote de idioma, `ocr.ler_texto` devolve None, o recurso se desliga inteiro e NADA quebra — e o ARRANQUE avisa alto, como `montar_despachante` ja faz sem .env (D-02)."
    - "`l2scanner/manutencao.py` nao importa winrt, nao importa cv2 e nao importa `l2scanner.ocr` — o tempo, o texto e os pixels entram por parametro, igual a `agenda.py` e `loot.py` (D-03)."
    - "O OCR roda a cada ~5s, NUNCA a cada tick, e os pixels so sao pedidos quando a busca vence — mesmo desenho do `VigiaDoCliente` (D-06)."
    - "Os dois avisos sao `Categoria.SEMPRE` e atravessam o silencio de TvT/Prime (D-08), dentro de `console.moldurar` (D-11)."
    - "`python -m l2scanner --testar-manutencao` mostra a regiao usada, salva o recorte em disco com o caminho completo e imprime o que o OCR leu e o que o parser entendeu (D-13)."
    - "A calibracao antiga do usuario continua carregando: `VERSAO_DO_ESQUEMA` segue em 2 e `banner_manutencao` e opcional (D-07)."
    - "A suite inteira segue verde (634+ testes), sem o jogo aberto, sem rede e SEM as bindings de OCR instaladas no Python que roda os testes."
  artifacts:
    - "l2scanner/manutencao.py — `eh_banner_de_manutencao`, `interpretar_banner`, `descrever_duracao`, `chave_do_marcador`, `texto_de_anuncio`, `texto_de_5_minutos`, `TipoDeAvisoDeManutencao`, `AvisoDeManutencao`, `VigiaDeManutencao`"
    - "l2scanner/ocr.py — `disponivel()`, `motivo_indisponivel()`, `ler_texto(pixels) -> str | None`, unico lugar do projeto que conhece WinRT"
    - "l2scanner/calibracao.py — campo `banner_manutencao: Regiao | None` e o acessor `regiao_do_banner(na_janela)`, SEM bump de versao de esquema"
    - "l2scanner/sessao.py — `Sessao.manutencao`, `_processar_manutencao`, `ResultadoDoTick.avisos_de_manutencao`"
    - "l2scanner/__main__.py — `montar_vigia_de_manutencao`, o extra `banner_manutencao`, a flag e o comando `--testar-manutencao`"
    - "requirements.txt — os seis pacotes `winrt-*`, com o comentario explicando o porque"
    - "vigiar-party.bat — UM unico bloco de checagem de dependencias, agora incluindo o modulo de OCR"
    - "tests/test_manutencao.py — parsing, negativas, consenso, ancora, expiracao, cadencia, marcador, regiao"
    - "tests/test_ocr.py — a degradacao graciosa sem as bindings"
    - "tests/test_sessao.py — `TestManutencaoNoTick`: os dois avisos na costura, SEMPRE, moldurados, uma vez so"
  key_links:
    - "`agora + tempo_lido` -> `momento_da_manutencao` (D-04): E O LINK CENTRAL. Depois dele o recurso inteiro passa a viver no relogio, e e o que faz o aviso de 5 minutos sobreviver ao banner sumir. Sem ele, jogo minimizado ou banner coberto matam o segundo aviso."
    - "consenso -> ancoragem (D-05): a ancora so e criada por DUAS leituras que concordam. Ancorar na primeira leitura faria um digito comido pelo OCR anunciar 'faltam 4 minutos' quando faltam 40 — e a party largaria o farm por nada."
    - "`VigiaDeManutencao.avaliar` -> `registro.marcar(aviso.chave)` no `Sessao` (D-09): a decisao de despachar E a chamada ao `marcar`, nunca uma checagem anterior. E o mesmo O_CREAT|O_EXCL que ja impede o grupo de receber o TvT em dobro."
    - "`chave_do_marcador` -> `RegistroEmDisco.podar` (D-09): a chave PRECISA comecar com a data ISO, senao `date.fromisoformat(nome.split('_',1)[0])` levanta, o `podar` pula o arquivo com `continue` e a pasta cresce para sempre."
    - "`cadencia vencida` -> `obter_pixels()` (D-06): passar um CHAMAVEL, e nao os pixels, e o que faz a cadencia valer alguma coisa — nos ticks sem busca o recorte nem e tocado."
    - "`frame.extras['banner_manutencao']` -> `JanelaSource._extra_para_janela` (D-07): o recorte vem do frame COMPLETO da janela, de graca. Se a regiao cair fora, `_extra_para_janela` devolve None e o recurso simplesmente nao le — nunca inventa."
    - "`ocr.disponivel()` -> `montar_vigia_de_manutencao` -> None (D-02): o unico ponto onde a ausencia das bindings desliga o recurso. Se o import de winrt subisse para o topo de um modulo que o scanner sempre carrega, quem nao atualizou o venv perderia o scanner INTEIRO por causa de um recurso opcional."
---

<objective>
Avisar a party no WhatsApp quando o servidor do XM Essence entra em
manutencao, lendo por OCR o banner que o jogo mostra por cima da party window.

Dois avisos, nao um: (1) assim que o anuncio aparece, dizendo o tempo como
esta na tela; (2) quando faltarem 5 minutos.

Purpose: a manutencao ja custou caro a este projeto uma vez. Em 2026-08-24 o
servidor caiu e o scanner passou 90 s e depois 5 min repetindo "sem visao da
party" sem nunca dizer o motivo — a Fase 5 nasceu disso. Mas a Fase 5 so sabe
reconhecer o servidor DEPOIS que ele caiu. Este trabalho e a outra metade: o
jogo ANUNCIA a manutencao com 40 minutos de antecedencia, em texto, na tela, e
o scanner atravessa esse anuncio inteiro sem ver. Quem esta AFK farmando perde
o loot do chao, perde o buff e cai no meio de uma instance por falta de um
aviso que estava escrito na tela o tempo todo.

Output: `l2scanner/manutencao.py` (logica pura), `l2scanner/ocr.py` (o unico
lugar que conhece WinRT), a fiacao no `Sessao` e no `__main__`, a ferramenta de
conferencia `--testar-manutencao`, e os testes que provam que o aviso de 5
minutos sai mesmo com o scanner cego.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

@l2scanner/cliente.py
@l2scanner/agenda.py
@l2scanner/sessao.py
</context>

<decisions_travadas>
Decisoes do usuario. NAO revisitar, NAO propor alternativa, NAO simplificar.
A numeracao D-NN corresponde as letras (a)..(m) do briefing.

- **D-01 (a)** — OCR, nao template-matching. O tempo muda a cada segundo, entao
  nao existe template de digito possivel sem construir 10 templates a partir de
  uma manutencao gravada. E o OCR dispensa arquivo de template ate para
  DETECTAR o banner — e isso que permite entregar hoje, sem depender de o
  usuario capturar uma imagem numa manutencao futura.
- **D-02 (b)** — Modulo novo `l2scanner/ocr.py`, unico lugar do projeto que
  conhece WinRT. Degradacao graciosa OBRIGATORIA: sem as bindings ou sem pacote
  de idioma, `ler_texto(pixels) -> str | None` devolve None, o recurso se
  desliga inteiro e o ARRANQUE AVISA ALTO (como `montar_despachante` ja faz
  quando falta o .env). Um `import winrt` no topo de um modulo que o scanner
  sempre carrega derrubaria quem nao atualizou o venv — o import tem que ser
  tolerante.
- **D-03 (c)** — Modulo novo `l2scanner/manutencao.py` com a logica PURA (tempo
  por parametro, sem relogio proprio, sem disco, sem OCR — mesma disciplina de
  `agenda.py` e `loot.py`): `eh_banner_de_manutencao(texto) -> bool`, tolerando
  `Maintence` e `Maintenance`, caixa e espacos; `interpretar_banner(texto) ->
  timedelta | None`, aceitando `40 minutes 26 seconds`, `5 minutes`,
  `26 seconds` e a forma com horas se aparecer; normalizando confusoes classicas
  de OCR (O->0, l/I->1, S->5) SOMENTE em contexto de digito — normalizar o texto
  inteiro quebraria a palavra `seconds`.
- **D-04 (d)** — ANCORA NO RELOGIO. Numa leitura bem sucedida,
  `momento_da_manutencao = agora + tempo_lido`. Dai em diante os dois avisos
  saem do RELOGIO ANCORADO (o `Relogio` que o projeto acabou de construir),
  nunca da tela. E o que faz o aviso de 5 minutos sobreviver a cegueira, jogo
  minimizado, banner coberto ou alt-tab. Re-ancorar a cada leitura bem sucedida
  (a leitura mais recente e a mais precisa).
- **D-05 (e)** — CONSENSO ANTES DE ANUNCIAR: exige DUAS leituras cujos momentos
  de manutencao implicados batam dentro de uma tolerancia curta. Sem isso, um
  digito comido pelo OCR anunciaria "faltam 4 minutos" quando faltam 40 — e o
  grupo largaria o farm por nada. Numa contagem de 40 minutos, atrasar o
  primeiro aviso uma cadencia (~5s) nao custa nada.
- **D-06 (f)** — CADENCIA: o OCR roda a cada ~5s, NUNCA a cada tick, exatamente
  pela razao ja documentada no `VigiaDoCliente` (matchTemplate de 45 ms seria
  ~98% do CPU a 1 Hz). Espelhar aquele desenho, inclusive o veredito que gruda
  entre buscas.
- **D-07 (g)** — A regiao vem de `frame.extras`, mecanismo que JA EXISTE (o
  `hp_proprio` usa). Regiao opcional `banner_manutencao` no `calibration.json`;
  sem ela, um padrao derivado da janela cobrindo a faixa superior esquerda, que
  e onde o banner aparece por cima da party window. Em modo `mss` sem a regiao
  configurada o recurso simplesmente nao liga — sem inventar deteccao onde nao
  ha pixels.
- **D-08 (h)** — Os DOIS avisos sao `Categoria.SEMPRE` e atravessam o silencio.
  Manutencao durante TvT/Prime e justamente quando o silencio esta ligado — e
  quando mais importa saber.
- **D-09 (i)** — Marcadores DURAVEIS no `.agenda/` via `RegistroEmDisco.marcar`
  (O_CREAT|O_EXCL, atomico), com A DATA NA FRENTE para a poda de 3 dias
  funcionar: `{YYYY-MM-DD}_manutencao-{HHMM}_anunciada` e
  `{YYYY-MM-DD}_manutencao-{HHMM}_faltam5`. Sem o prefixo de data o `podar()`
  pula o arquivo e a pasta cresce para sempre. Chave derivada do MOMENTO DA
  MANUTENCAO, nao do momento do aviso — e o que faz as duas instancias
  convergirem para a mesma chave.
- **D-10 (j)** — O aviso de 5 minutos dispara pelo RELOGIO mesmo se o banner
  nao estiver mais visivel. Robustez contra cegueira vale mais do que tratar
  manutencao cancelada. A ancora EXPIRA depois que o momento passa (com uma
  folga curta), para nao reavisar nem carregar ancora velha.
- **D-11 (k)** — As duas mensagens saem dentro de `console.moldurar(texto,
  hora)`, como os avisos de agenda passaram a sair.
- **D-12 (l)** — `requirements.txt` ganha os pacotes winrt COM COMENTARIO
  explicando o porque (no estilo do arquivo, que justifica cada dependencia), e
  a checagem de import do `vigiar-party.bat` (hoje `import
  mss,cv2,numpy,windows_capture`) ganha o modulo de OCR para o `.venv` antigo se
  atualizar sozinho. ATENCAO: o `.bat` tem esse bloco de checagem DUPLICADO
  (dois trechos identicos) — trate os dois ou consolide.
- **D-13 (m)** — Uma ferramenta de conferencia, `python -m l2scanner
  --testar-manutencao`: captura a janela agora, mostra qual regiao esta usando,
  salva o recorte em disco para o usuario olhar, e imprime exatamente o que o
  OCR leu e o que o parser entendeu. E a unica forma de o usuario validar
  sozinho na proxima manutencao aquilo que o spike nao provou (a fonte do jogo).

**O SPIKE JA FOI EXECUTADO E APROVADO — nao repetir, nao re-verificar:**

- `winrt-Windows.Media.Ocr` e companheiros instalaram no `.venv` (Python
  3.12.10) sem erro. Conferido em disco: `winrt_windows_media_ocr-3.2.1`,
  `winrt_windows_graphics_imaging-3.2.1`, `winrt_windows_storage_streams-3.2.1`,
  `winrt_windows_globalization-3.2.1`, `winrt_windows_foundation-3.2.1`,
  `winrt_windows_foundation_collections-3.2.1`, `winrt_runtime-3.2.1`.
- Os pacotes de idioma existem: `C:\Windows\OCR` tem `en-us` e `pt-br`.
- Um banner SINTETICO (cv2.putText, fundo escuro) foi lido como
  `'Server Maintence 40 minutes 26 seconds'` — texto exato, incluindo o typo.
- O caminho WinRT que funcionou, e que o Task 3 deve REPRODUZIR, nao redescobrir:
  `InMemoryRandomAccessStream` + `DataWriter.write_bytes` do PNG codificado por
  `cv2.imencode`, `BitmapDecoder.create_async`, `get_software_bitmap_async`,
  `OcrEngine.try_create_from_language(Language("en-US"))` com fallback para
  `try_create_from_user_profile_languages()`, `recognize_async(bitmap).text` —
  tudo dentro de um `asyncio.run`.

**RISCO REGISTRADO, e a razao de D-13 existir:** a precisao do OCR na FONTE DO
JOGO nao foi provada. So uma manutencao real (ou um PNG salvo pelo usuario)
prova isso. Nada neste plano finge o contrario, e nenhum criterio de sucesso
automatico depende disso.

**DESCOBERTA DE AMBIENTE QUE MOLDA TODOS OS TESTES:** o Python que roda a suite
(system, 3.12.10, pytest 9.1.1) **NAO tem as bindings de winrt** — so o `.venv`
tem. Isso e um presente: o caminho "sem bindings" e o caminho PADRAO da suite.
Consequencia obrigatoria: nenhum teste pode depender de uma leitura de OCR bem
sucedida. Todo teste que precisa de texto injeta um `ler_texto` falso.

**GOAL-01** — avisar assim que o anuncio aparece, dizendo o tempo COMO ESTA NA
TELA. **GOAL-02** — avisar quando faltarem 5 minutos.

**Fora de escopo, e nao negociavel:** nenhuma mudanca em `visao.py`,
`rastreador.py` ou `identidade.py`. Este recurso e ORTOGONAL a deteccao de
party — ele nunca olha uma barra de HP e nunca produz um `Evento` do
rastreador.
</decisions_travadas>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: o caminho inteiro, de um texto de banner ate a mensagem despachada</name>
  <files>tests/test_manutencao.py, tests/test_sessao.py, l2scanner/manutencao.py, l2scanner/sessao.py</files>
  <read_first>
    - `l2scanner/agenda.py` linhas 99-123 (`Aviso.chave`) e 233-345 (`RegistroEmDisco`, `marcar`, `podar`) — o formato de chave duravel e a atomicidade O_CREAT|O_EXCL que D-09 reusa inteira. Repare no `nome.split("_", 1)[0]` do `podar`: e ele que exige a data na frente.
    - `l2scanner/sessao.py` linhas 53-88 (`ResultadoDoTick`), 139-157 (`_despachar`), 159-228 (`tick`) e 229-268 (`_processar_agenda`) — o molde exato: cru no resultado, moldurado no despacho, `Categoria.SEMPRE`, e o `marcar` como a decisao de despachar.
    - `l2scanner/console.py` linhas 97-120 (`moldurar`) — D-11.
    - `tests/test_sessao.py` linhas 44-79 (fixtures `calibracao`, `frame_real`, helper `nova_sessao`, helper `em`) e 323-353 (`TestBug1DestacarComUmArgumento`) — o helper que este task estende e o padrao de assercao de categoria.
  </read_first>
  <behavior>
    RED primeiro. Escreva estes testes, veja falhar, so entao implemente.

    Em `tests/test_manutencao.py` (arquivo novo), classe `TestLeituraDoBanner`:

    - **o banner real do jogo e reconhecido e interpretado.** Texto
      `"Server Maintence 40 minutes 26 seconds Please avoid entering instance"`:
      `eh_banner_de_manutencao(...)` e True e `interpretar_banner(...)` e
      `timedelta(minutes=40, seconds=26)`. Este e o texto EXATO que o spike leu.
    - **a grafia correta tambem vale.** `"Server Maintenance 5 minutes"` ->
      True e `timedelta(minutes=5)`.
    - **caixa e espaco nao importam.** `"  SERVER   MAINTENCE   26 SECONDS "` ->
      True e `timedelta(seconds=26)`.
    - **as confusoes de OCR viram digito — e SO em contexto de digito (D-03).**
      `"Server Maintence 4O minutes 2l seconds"` -> `timedelta(minutes=40,
      seconds=21)`. E, na mesma classe de teste, a prova de que a normalizacao
      nao atropela a lingua: `"Server Maintenance 5 seconds"` continua
      `timedelta(seconds=5)` — a palavra `seconds` sai INTACTA, e um token sem
      nenhum digito de verdade (`"SO"`) nao vira numero. Comente que normalizar
      o texto inteiro era o caminho obvio e errado: ele quebraria justamente a
      palavra que da sentido ao numero.
    - **a forma com horas, se aparecer.** `"Server Maintence 1 hour 5 minutes"`
      -> `timedelta(hours=1, minutes=5)`.
    - **texto que nao e o banner nao vira nada (D-03).** Para cada uma destas —
      `"You cannot use this item because the server will restart in a few minutes"`
      (frase REAL dos prints do usuario), `"Please avoid entering instance"`,
      `"Korzis 40 minutes"`, `""` e `None` — `eh_banner_de_manutencao` e False.
      Comente no teste que a primeira frase e o teste mais importante do arquivo:
      ela contem `server`, `restart` e `minutes` e mesmo assim NAO pode virar
      manutencao.

    Em `tests/test_manutencao.py`, classe `TestChaveDoMarcador`:

    - **a chave comeca com a data ISO e sobrevive ao `podar` (D-09).** Monte um
      `RegistroEmDisco(tmp_path)`, marque a chave de um momento de 4 dias atras,
      chame `podar()` e afirme que ela foi apagada. Depois marque a chave de um
      momento de hoje, chame `podar()` e afirme que ela FICOU. Sem o prefixo de
      data o primeiro caso falha silenciosamente (o `podar` da `continue`), e
      esse e exatamente o defeito que D-09 manda evitar.
    - **a chave sai do MOMENTO DA MANUTENCAO, nao do momento do aviso.** Duas
      chamadas a `chave_do_marcador(momento, tipo)` feitas com o mesmo `momento`
      dao a mesma string, e os dois tipos dao strings DIFERENTES.

    Em `tests/test_sessao.py`, classe nova `TestManutencaoNoTick` (depois de
    `TestLootNoTick`) — a costura, que e onde os erros deste projeto moram:

    - **o anuncio atravessa vigia, marcador, resultado e despacho.** Monte uma
      `Sessao` com `manutencao=VigiaDeManutencao(ler_texto=lambda _: "Server
      Maintence 40 minutes 26 seconds")` e um `frame` cujo
      `extras={"banner_manutencao": <array 10x10 qualquer>}`. Rode DOIS ticks
      espacados de 6 s (o consenso de D-05 exige duas leituras). Afirme que:
      `resultado.avisos_de_manutencao == [TipoDeAvisoDeManutencao.ANUNCIADA]`,
      que existe exatamente UM despacho com `Categoria.SEMPRE`, que o texto
      despachado contem `"***"` (a moldura de D-11) e que o texto contem
      `"40 minutos"` e `"26 segundos"`.
    - **sai UMA vez so em muitos ticks.** Rode 30 ticks seguidos com o mesmo
      texto. Afirme que o total de avisos de manutencao continua 1.
  </behavior>
  <action>
    Implemente o caminho fino inteiro numa passada so — leitura, chave, texto,
    vigia minimo e costura no `Sessao` — para que UMA manutencao anunciada
    funcione de ponta a ponta antes de qualquer refinamento entrar. O consenso,
    a re-ancora, o aviso de 5 minutos e a expiracao sao do Task 2; aqui basta o
    consenso simples que o teste dos dois ticks exige, ja no formato final.

    **`l2scanner/manutencao.py` — arquivo novo.** Docstring no estilo do
    projeto, explicando o PORQUE: a Fase 5 so reconhece o servidor DEPOIS que
    ele cai; o jogo ANUNCIA a queda com 40 minutos de antecedencia, em texto, e
    o scanner atravessava esse anuncio inteiro sem ver. E, com igual destaque, a
    disciplina: tempo por parametro, sem relogio proprio, sem disco, sem OCR —
    o mesmo motivo de `agenda.py` (testar "faltam 5 minutos" nao pode exigir
    esperar 35 minutos).

    IMPORTS PROIBIDOS NESTE MODULO: `winrt`, `cv2`, `l2scanner.ocr`. Existe um
    teste no Task 3 que le a arvore de imports com `ast` e falha se algum
    aparecer.

    - `eh_banner_de_manutencao(texto: str | None) -> bool`: normaliza para
      minusculas e procura a RAIZ `mainten`, que cobre `maintence` e
      `maintenance` de uma vez. Documente por que a raiz sozinha basta e por que
      exigir tambem a palavra `server` seria PIOR: um `5erver` mal lido pelo OCR
      derrubaria a deteccao inteira, enquanto `mainten` e o token mais raro da
      tela. Documente tambem que essa e a primeira das TRES portas contra
      inventar manutencao — as outras duas sao exigir uma duracao interpretavel
      e exigir o consenso de D-05.
    - `_normalizar_digitos(texto: str) -> str`: separa em tokens por espaco e,
      para cada token que JA CONTEM ao menos um digito de verdade, troca
      `O/o->0`, `l/I->1`, `S/s->5`. Tokens sem digito nenhum ficam INTACTOS.
      Escreva numa linha de comentario a razao exata: sem a exigencia do digito
      real, `SO` viraria `50` e qualquer palavra da tela poderia virar numero —
      e `seconds` sobreviver e o requisito literal de D-03.
    - `interpretar_banner(texto: str | None) -> timedelta | None`: aplica
      `_normalizar_digitos`, depois procura, em minusculas, `(\d+)\s*hour`,
      `(\d+)\s*minut` e `(\d+)\s*second` — prefixos, nao palavras inteiras, para
      tolerar plural e truncamento do OCR. Devolve None quando NENHUM componente
      aparece, e None tambem quando o total passa de 24 h (leitura de lixo).
      `timedelta(0)` e resultado legitimo: os prints do usuario tem
      `00 minutes 00 seconds`, que significa "agora".
    - `descrever_duracao(d: timedelta) -> str`: `"40 minutos e 26 segundos"`,
      `"5 minutos"`, `"26 segundos"`, com horas quando houver. E o "tempo como
      esta na tela" de GOAL-01, entao nao arredonde.
    - `class TipoDeAvisoDeManutencao(Enum)`: `ANUNCIADA = "anunciada"`,
      `FALTAM5 = "faltam5"`. Os valores entram na chave — nao os mude depois.
    - `chave_do_marcador(momento: datetime, tipo) -> str`: exatamente
      `f"{momento.date().isoformat()}_manutencao-{HH}{MM}_{tipo.value}"`, com o
      momento ARREDONDADO PARA O MINUTO mais proximo. Documente a aresta e a
      escolha: duas instancias podem implicar momentos separados por ~1 s e, se
      esse instante cair em cima de um `:30`, cada uma arredonda para um lado e
      o grupo recebe a mensagem em dobro. Isso e ACEITO — o `RegistroEmDisco` ja
      declara a mesma preferencia ("preferir o aviso duplicado ao aviso
      perdido"), e aqui o aviso perdido e uma manutencao que ninguem soube.
    - `@dataclass(frozen=True) class AvisoDeManutencao`: `tipo`, `momento`
      (datetime da manutencao), `texto`; propriedade `chave` delegando para
      `chave_do_marcador`.
    - `texto_de_anuncio(momento, duracao) -> str`: precisa carregar OS DOIS
      fatos — a duracao lida (`descrever_duracao`) e a hora de parede
      (`HH:MM`) — porque o primeiro e o que o usuario pediu e o segundo e o que
      permite a party se organizar. Inclua a instrucao de nao entrar em
      instance, que e o que o proprio banner diz.
    - `class VigiaDeManutencao`: `__init__(self, ler_texto, ...)`. `ler_texto` e
      OBRIGATORIO e entra por parametro — e o que mantem este modulo sem OCR e
      o que permite os testes injetarem texto. Neste task implemente
      `avaliar(self, obter_pixels, agora) -> list[AvisoDeManutencao]` com:
      cadencia (Task 2 detalha), leitura, e consenso de duas leituras
      concordantes produzindo a ancora e UM `AvisoDeManutencao` ANUNCIADA. Um
      conjunto em memoria guarda quais tipos ja foram emitidos NESTA ancora.

    **`l2scanner/sessao.py`**:
    - `ResultadoDoTick` ganha `avisos_de_manutencao: list = field(default_factory=list)`.
      Estruturado, e nao so texto, pelo mesmo motivo de `despachos` existir.
    - `Sessao.__init__` ganha `manutencao=None` no fim da lista de parametros.
      Default None mantem TODA chamada existente intacta.
    - `_processar_manutencao(self, agora, frame, resultado)`: sai cedo se
      `self.manutencao is None`; chama
      `self.manutencao.avaliar(lambda: frame.extras.get("banner_manutencao"), agora)`;
      para cada aviso, `if not self.registro.marcar(aviso.chave): continue`,
      depois `resultado.avisos.append(aviso.texto)` (cru — o console monta a
      propria moldura a partir de `avisos`), `resultado.avisos_de_manutencao.append(aviso.tipo)`
      e `self._despachar(moldurar(aviso.texto, agora.strftime("%H:%M")), Categoria.SEMPRE, resultado=resultado)`
      — `SEMPRE` por D-08 (manutencao durante TvT/Prime e quando mais importa
      saber) e `moldurar` por D-11.
    - Chame-o em `tick`, IMEDIATAMENTE depois de `self._processar_agenda(...)` e
      ANTES do `try: observacao = extrair(...)`. Escreva o porque numa linha:
      pelo mesmo motivo que a agenda vem antes, um erro de leitura da party nao
      pode engolir o aviso de manutencao junto — e o `except` daquele bloco
      retorna cedo.

    **`tests/test_sessao.py`**: acrescente `manutencao=None` ao helper
    `nova_sessao` e repasse ao `Sessao`. Nao mexa em mais nada do arquivo.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py tests/test_sessao.py -q</automated>
  </verify>
  <done>Um texto de banner injetado atravessa vigia, consenso de duas leituras, marcador durável em disco, resultado e despacho: sai UMA mensagem, com `Categoria.SEMPRE`, moldurada, dizendo o tempo como está na tela — e uma frase que não é o banner não produz nada.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: o vigia completo — cadencia, consenso, re-ancora, 5 minutos e expiracao</name>
  <files>tests/test_manutencao.py, tests/test_sessao.py, l2scanner/manutencao.py</files>
  <read_first>
    - `l2scanner/cliente.py` linhas 211-277 (`VigiaDoCliente`) — O MOLDE deste task. A tabela de custos na docstring, o `obter_pixels` chamavel, o `vencido = ultima is None or agora - ultima >= intervalo`, e o veredito que GRUDA entre buscas. D-06 pede espelhar este desenho.
    - `tests/test_cliente.py` linhas 307-453 (`TestVigiaDoCliente`) — o padrao de teste de cadencia: contador de chamadas, tempo por parametro, e o teste `test_os_pixels_so_sao_pedidos_quando_a_busca_vence`.
    - `l2scanner/relogio.py` linhas 146-165 (`agora_epoch`, `agora`) — de onde vem o `agora` que ancora tudo (D-04).
    - `l2scanner/manutencao.py` — o que o Task 1 escreveu.
  </read_first>
  <behavior>
    Estes sao os testes que o usuario pediu nominalmente. Todos RED antes da
    implementacao correspondente.

    Em `tests/test_manutencao.py`, classe `TestCadencia`:

    - **o OCR nao roda a cada tick (D-06).** Um `ler_texto` que conta chamadas,
      `obter_pixels` que conta chamadas. Rode `avaliar` a cada 1 s durante 12 s
      simulados. Afirme que houve 3 leituras (t=0, 5, 10), nao 12.
    - **os pixels so sao pedidos quando a busca vence.** Mesmo cenario: o
      contador de `obter_pixels` acompanha o de `ler_texto`, nunca o de ticks.
      Passar um CHAMAVEL e o que faz a cadencia valer alguma coisa.
    - **pixels None nao quebram e nao consomem consenso.** `obter_pixels`
      devolvendo None em varios ticks: nenhum aviso, nenhuma excecao.

    Classe `TestConsenso`:

    - **duas leituras concordantes anunciam.** 40 min em t=0 e 40 min (menos os
      5 s decorridos, ou seja `39 minutes 55 seconds`) em t=5. Um aviso
      ANUNCIADA. Afirme que `vigia.momento` e o instante implicado, com
      tolerancia de segundos.
    - **a leitura discrepante NAO anuncia (D-05).** Sequencia 40, depois 4,
      depois 40 minutos, uma leitura por cadencia. Afirme ZERO avisos. Este e o
      teste que o usuario descreveu com todas as letras — comente no teste que
      sem ele um digito comido pelo OCR faria a party largar o farm por nada.
    - **uma leitura discrepante nao move uma ancora ja confirmada.** Ancore com
      duas leituras de 40. Depois entregue uma leitura de 4 minutos. Afirme que
      `vigia.momento` NAO mudou e que nenhum aviso extra saiu.
    - **a re-ancora acontece dentro da tolerancia (D-04).** Depois de ancorado,
      uma leitura que implica um momento 20 s diferente ATUALIZA `vigia.momento`
      — a leitura mais recente e a mais precisa.
    - **uma manutencao REMARCADA re-ancora com duas leituras concordantes.**
      Ancorado em 40 min, entregue duas leituras seguidas de 90 min. Afirme que
      `vigia.momento` passou para o novo instante e que um ANUNCIADA novo saiu
      (a ancora anterior nao pode prender o vigia num horario que nao existe
      mais).

    Classe `TestAncoraSobreviveACegueira` — o coracao de D-10:

    - **o aviso de 5 minutos sai com o OCR devolvendo None depois (GOAL-02).**
      Ancore com duas leituras de `"Server Maintence 8 minutes"`. Depois troque
      o `ler_texto` por um que devolve None (banner sumiu / jogo coberto) e
      avance o tempo simulado ate faltarem 4 minutos, um tick por segundo.
      Afirme que UM aviso FALTAM5 saiu, que o texto dele nomeia o horario da
      manutencao, e que ele saiu SEM nenhuma leitura bem sucedida no meio.
      Comente que isto e a razao inteira de a ancora existir.
    - **os dois avisos saem quando o scanner sobe com pouco tempo restante.**
      Duas leituras de `"Server Maintence 3 minutes"`: ANUNCIADA e FALTAM5 saem,
      nessa ordem, no mesmo instante. E o texto do FALTAM5 diz 3 minutos, nao 5
      — o aviso nunca mente sobre o tempo que resta.
    - **cada tipo sai UMA vez so.** 200 ticks depois da ancoragem produzem
      exatamente um ANUNCIADA e um FALTAM5.

    Classe `TestExpiracao` (D-10):

    - **a ancora expira depois do momento, com folga.** Ancore, avance para
      depois de `momento + folga`, e afirme que `vigia.momento is None`.
    - **nao reavisa depois de expirar.** Depois da expiracao, continue rodando
      ticks com `ler_texto` devolvendo None: zero avisos novos.
    - **depois de expirar, uma manutencao nova pode ser anunciada.** Duas
      leituras novas voltam a produzir ANUNCIADA — a expiracao limpa o conjunto
      de emitidos, senao o proximo anuncio de verdade morreria em silencio.

    Em `tests/test_sessao.py`, na `TestManutencaoNoTick`:

    - **as duas instancias competindo pelo mesmo marcador (D-09).** Duas
      `Sessao` com registros apontando para a MESMA `tmp_path` e vigias
      independentes, alimentadas com o mesmo texto e o mesmo `agora`. Afirme
      que, somando as duas, sai exatamente UM despacho de ANUNCIADA. Este e o
      teste que prova que o `marcar` e a decisao de despachar, e nao uma
      checagem anterior.
    - **o FALTAM5 tambem atravessa a costura com `Categoria.SEMPRE` e
      moldurado.** Mesma montagem do Task 1, texto de 6 minutos, ticks ate
      faltarem 5: dois despachos, os dois `SEMPRE`, os dois com moldura.
  </behavior>
  <action>
    Complete `VigiaDeManutencao`. Nao acrescente parametro novo ao `avaliar` e
    nao introduza um relogio proprio: `agora` e um `datetime` que entra por
    parametro, e e o UNICO relogio deste modulo. O `Sessao` ja passa o `agora`
    derivado do `Relogio` ancorado — misturar `time.monotonic()` aqui repetiria
    literalmente o bug 2 documentado no topo de `sessao.py`.

    Constantes nomeadas, no topo do modulo, cada uma com o porque em comentario:
    `SEGUNDOS_ENTRE_LEITURAS = 5.0` (D-06, o mesmo numero e o mesmo motivo do
    `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO`), `TOLERANCIA_DO_CONSENSO =
    timedelta(seconds=60)` (folgada contra o atraso de leitura e parse,
    minuscula contra um digito comido — 4 min contra 40 min sao 36 minutos de
    diferenca), `ANTECEDENCIA = timedelta(minutes=5)` (GOAL-02),
    `FOLGA_APOS_A_MANUTENCAO = timedelta(minutes=10)` (D-10).

    Estado interno: `_ultima_leitura` (datetime da ultima vez que a cadencia
    venceu), `_ancora` (datetime confirmado, ou None), `_candidata` (datetime
    implicado por uma leitura ainda nao confirmada), `_duracao_confirmada` (a
    duracao lida na leitura que confirmou — e ela que entra no texto de
    GOAL-01), `_emitidos` (conjunto de `TipoDeAvisoDeManutencao`).

    `avaliar(obter_pixels, agora)`, nesta ordem exata:

    1. **Expirar primeiro.** Se ha ancora e `agora > ancora + folga`: zera
       ancora, candidata, duracao e `_emitidos`. Limpar `_emitidos` e
       obrigatorio — sem isso a proxima manutencao de verdade seria detectada e
       nunca anunciada, que e o pior modo de falha deste projeto.
    2. **Cadencia.** Se venceu, marque `_ultima_leitura = agora`, chame
       `obter_pixels()`; se nao for None, chame `self._ler(pixels)`; se voltou
       texto E `eh_banner_de_manutencao(texto)` E `interpretar_banner(texto)`
       nao e None, registre a leitura com `implicado = agora + duracao` (D-04).
    3. **Registrar a leitura**, com a regra de consenso de D-05:
       - com ancora e `abs(implicado - ancora) <= tolerancia`: RE-ANCORA
         (`_ancora = implicado`), sem tocar em `_emitidos` — e a mesma
         manutencao, so que medida melhor;
       - com ancora e FORA da tolerancia: NAO move a ancora. Se a candidata
         existe e o implicado bate com ela dentro da tolerancia, e uma
         manutencao REMARCADA confirmada por duas leituras: `_ancora =
         implicado`, `_emitidos` zerado, candidata limpa. Senao, `_candidata =
         implicado`;
       - sem ancora: se a candidata existe e bate dentro da tolerancia,
         CONFIRMA (`_ancora = implicado`, guarda a duracao, limpa a candidata);
         senao vira a nova candidata.
    4. **Montar os avisos devidos a partir da ANCORA, sempre** — inclusive nos
       ticks em que nao houve leitura nenhuma. E este passo, e so ele, que faz o
       aviso de 5 minutos sobreviver a cegueira (D-10). ANUNCIADA quando ha
       ancora e o tipo nao esta em `_emitidos`. FALTAM5 quando ha ancora,
       `ancora - agora <= ANTECEDENCIA` e o tipo nao esta em `_emitidos`.
       Acrescente cada tipo emitido a `_emitidos` ao montar. ANUNCIADA vem
       primeiro na lista.

    `_ler(pixels)` envolve `self._ler_texto(pixels)` num `try/except Exception
    -> None`. Cinto e suspensorio: `ocr.ler_texto` ja promete nao levantar, mas
    o vigia roda dentro do tick de captura e uma excecao aqui pararia o scanner
    de olhar a party — que e o unico defeito que este projeto trata como
    inaceitavel.

    `texto_de_5_minutos(momento, restante)`: diz os minutos REAIS que faltam,
    calculados da ancora, e a hora de parede. Documente por que ele nao pode
    dizer "5" fixo: quando o scanner sobe no meio de uma contagem de 3 minutos,
    o aviso sai atrasado e cravar "5" seria mentir sobre o unico numero que
    importa.

    Propriedade publica `momento -> datetime | None` devolvendo a ancora. Os
    testes e o `--testar-manutencao` leem por ela; nao exponha os atributos
    privados.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_manutencao.py tests/test_sessao.py -q</automated>
  </verify>
  <done>A cadencia le a cada 5 s e nao a cada tick; uma leitura discrepante entre duas boas nao anuncia; a ancora sobrevive ao OCR devolver None e dispara o aviso de 5 minutos pelo relogio; cada aviso sai uma vez so, inclusive entre duas instancias; a ancora expira sem reavisar e sem bloquear a proxima manutencao.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: `ocr.py` tolerante e a regiao do banner na calibracao</name>
  <files>tests/test_ocr.py, tests/test_manutencao.py, l2scanner/ocr.py, l2scanner/calibracao.py</files>
  <read_first>
    - `l2scanner/calibracao.py` linhas 20-25 (`VERSAO_DO_ESQUEMA`), 118-155 (os campos opcionais `hp_proprio`, `janela`, `party_window_na_janela`), 193-217 (`salvar`) e 218-260 (`carregar`) — o padrao exato de campo opcional que entra e sai do JSON por `.get`, sem bump de versao.
    - `l2scanner/frames.py` linhas 44-108 (`Frame.extras` e `Regiao`) — o retangulo e a advertencia sobre coordenadas negativas.
    - `l2scanner/cliente.py` linhas 119-140 (`carregar_template` e `FAIXA_DO_DIALOGO`) — o precedente de "regiao generosa de proposito, em fracoes, com o porque medido no comentario".
    - `l2scanner/relogio.py` linhas 60-79 (`epoch_do_cabecalho_date`) — o precedente de "esta funcao NUNCA levanta, e o porque".
  </read_first>
  <behavior>
    ATENCAO AO AMBIENTE: o Python que roda a suite NAO tem as bindings de
    winrt. Todo teste abaixo tem que passar nesse Python E no `.venv` do
    usuario, que tem. Onde o resultado dependeria do ambiente, force o estado
    com `monkeypatch` em vez de torcer.

    Em `tests/test_ocr.py` (arquivo novo):

    - **importar o modulo nunca levanta.** `import l2scanner.ocr` funciona com
      ou sem as bindings. Este teste sozinho e a prova de D-02: um import de
      winrt no topo derrubaria quem nao atualizou o venv.
    - **sem as bindings, `ler_texto` devolve None e nao levanta.** Force a
      indisponibilidade por `monkeypatch` no cache interno do motivo e chame
      `ler_texto(np.zeros((20, 100, 3), dtype=np.uint8))`. Afirme None.
    - **sem as bindings, `motivo_indisponivel()` diz o que fazer.** Texto nao
      vazio, mencionando o caminho de conserto (`vigiar-party.bat` ou o
      `pip install -r requirements.txt`). Um aviso que nao diz como consertar e
      ruido.
    - **entrada degenerada nao chega perto do WinRT.** `ler_texto(None)` e
      `ler_texto(array vazio)` devolvem None mesmo com o OCR disponivel — a
      guarda vem ANTES de qualquer chamada de plataforma.
    - **`ler_texto` engole a excecao da plataforma.** `monkeypatch` na funcao
      interna de reconhecimento para levantar `RuntimeError`; afirme None e
      nenhuma excecao vazando.
    - **o contrato de tipo se sustenta no ambiente real.** Chamada com uma
      imagem qualquer: o retorno e None OU `str`, nos dois ambientes. E o teste
      que nao mente sobre o que nao foi provado.

    Em `tests/test_manutencao.py`, classe `TestModuloPuro`:

    - **`manutencao.py` nao importa winrt, cv2 nem `l2scanner.ocr` (D-03).**
      Leia o arquivo, monte a arvore com `ast`, colete todo `Import` e
      `ImportFrom` e afirme que nenhum nome comeca com `winrt`, e igual a `cv2`,
      ou termina em `ocr`. Assercao estrutural de proposito: uma regra de
      arquitetura que so vive num comentario e uma regra que ja quebrou.

    Em `tests/test_manutencao.py`, classe `TestRegiaoDoBanner` (D-07):

    - **a regiao calibrada vence o padrao.** Com `banner_manutencao` preenchida,
      `cal.regiao_do_banner(na_janela=True)` devolve exatamente ela.
    - **sem calibracao, no caminho `--janela`, o padrao cobre o canto superior
      esquerdo da party window.** Afirme que a regiao devolvida contem o ponto
      `(party.esquerda, party.topo)` e que e MAIS LARGA que a party window — o
      banner e mais largo que as barras.
    - **sem calibracao, no caminho `mss`, devolve None.** E o "simplesmente nao
      liga" de D-07: sem inventar deteccao onde nao ha pixels.
    - **o padrao nunca sai com coordenada negativa.** Party window em (0, 0):
      `esquerda` e `topo` da regiao continuam >= 0.
    - **a calibracao v2 antiga carrega sem a chave nova.** Salve uma
      `Calibracao` sem `banner_manutencao`, recarregue, afirme None e nenhuma
      excecao. E depois: com a regiao preenchida, `salvar` -> `carregar`
      devolve a mesma `Regiao` (ida e volta).
    - **a versao do esquema NAO mudou.** `calibracao.VERSAO_DO_ESQUEMA == 2`.
      Um bump invalidaria o `calibration.json` real do usuario e o forcaria a
      recalibrar por causa de um recurso opcional.
  </behavior>
  <action>
    **`l2scanner/ocr.py` — arquivo novo, o unico do projeto que conhece WinRT
    (D-01, D-02).**

    Docstring explicando o PORQUE de o modulo existir isolado (D-02): o Windows
    11 ja tem um motor de OCR embutido, gratuito e offline, mas as bindings sao
    modulares desde set/2023 e podem simplesmente nao estar no `.venv` de quem
    nao rodou o `vigiar-party.bat` depois desta atualizacao. O recurso de
    manutencao e opcional; o scanner nao e. Entao a ausencia das bindings
    desliga o recurso e nao o produto.

    - `disponivel() -> bool` e `motivo_indisponivel() -> str | None`, com o
      resultado calculado UMA vez e guardado em modulo (`_MOTIVO`, `_CHECADO`).
      Calcule PREGUICOSAMENTE, na primeira pergunta — importar o modulo nao pode
      custar o import do WinRT. Dois motivos distintos, com textos distintos:
      bindings ausentes (diz para rodar o `vigiar-party.bat`, que reinstala
      sozinho) e motor nulo (diz para procurar a pasta `C:\Windows\OCR` e
      instalar o idioma Ingles (EUA)). Um aviso que nao diz como consertar e
      ruido.
    - `ler_texto(pixels) -> str | None`: guarda contra None e array vazio ANTES
      de tudo; devolve None se indisponivel; `asyncio.run(...)` do caminho do
      spike; `except Exception` -> `log.debug` + None. Documente numa linha por
      que esta funcao NUNCA levanta: ela roda dentro do tick de captura, e uma
      excecao aqui pararia o scanner de olhar a party.
    - REPRODUZA o caminho do spike, sem redescobrir: `cv2.imencode(".png",
      ampliado)`; `InMemoryRandomAccessStream()`; `DataWriter(stream)` com
      `write_bytes`, `await store_async()`, `await flush_async()`;
      `stream.seek(0)`; `await BitmapDecoder.create_async(stream)`; `await
      decoder.get_software_bitmap_async()`;
      `OcrEngine.try_create_from_language(Language("en-US"))` com fallback para
      `try_create_from_user_profile_languages()`; `await
      engine.recognize_async(bitmap)` e o `.text`.
    - `ESCALA = 3` com `cv2.INTER_CUBIC` antes de codificar, e um comentario com
      a justificativa: fonte de UI de jogo e pequena e estilizada, ampliar antes
      do OCR e a recomendacao da propria pesquisa de stack do projeto, e a 0,2 Hz
      o custo e irrelevante. O motor de OCR pode ser guardado em modulo (criar a
      cada 5 s e desperdicio).
    - `asyncio` e `cv2` sao importados no topo (ambos ja sao dependencia dura);
      os simbolos de `winrt` so dentro da funcao de checagem/reconhecimento.

    **`l2scanner/calibracao.py`**:
    - Campo novo `banner_manutencao: Regiao | None = None`, depois de
      `party_window_na_janela` e ANTES de `versao`. Comentario explicando que e
      opcional e por que existe: a regiao padrao e um palpite educado sobre onde
      o banner cai, e o `--testar-manutencao` e como o usuario descobre se
      acertou — errando, ele corrige AQUI, sem tocar em codigo.
    - Entra no `salvar` e sai do `carregar` com `.get`, exatamente como
      `hp_proprio`. **NAO BUMPE `VERSAO_DO_ESQUEMA`** — escreva o porque numa
      linha de comentario junto ao campo: a constante vale 2 e o `carregar`
      recusa qualquer outro valor, entao subir para 3 invalidaria o
      `calibration.json` real do usuario e o obrigaria a recalibrar por causa de
      um campo opcional.
    - `regiao_do_banner(self, na_janela: bool) -> Regiao | None`: devolve
      `self.banner_manutencao` quando ela existe; senao, quando `na_janela` e ha
      `party_window_na_janela`, devolve a faixa derivada; senao None (D-07).
      A derivacao usa constantes nomeadas — margem a esquerda, margem acima,
      largura extra e altura maxima — com o comentario dizendo que o banner
      aparece POR CIMA da party window, e mais largo que as barras, e que
      generoso e melhor que justo aqui porque `eh_banner_de_manutencao` exige a
      raiz `mainten` e texto vizinho e so ruido. Clampe `esquerda` e `topo` em
      zero.
    - Documente numa linha a ambiguidade de referencial: `banner_manutencao`,
      como `hp_proprio`, vale para o caminho `--janela`; quem configurar a mao
      para o caminho `mss` precisa escrever coordenadas de desktop. O
      `--testar-manutencao` imprime a regiao justamente para essa conferencia.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_ocr.py tests/test_manutencao.py -q && python -c "from pathlib import Path; from l2scanner.calibracao import Calibracao; c = Calibracao.carregar(Path('calibration.json')); print('calibracao real OK, banner:', c.banner_manutencao)"</automated>
  </verify>
  <done>`ocr.py` devolve None e explica o motivo sem as bindings, sem nunca levantar e sem custar o import do WinRT a quem so importa o modulo; `manutencao.py` nao importa OCR nenhum (provado por `ast`); a calibracao REAL do usuario continua carregando e a regiao do banner sai calibrada, derivada ou None conforme o modo.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: fiacao no arranque, `--testar-manutencao`, requirements e o `.bat`</name>
  <files>tests/test_manutencao.py, l2scanner/__main__.py, requirements.txt, vigiar-party.bat</files>
  <read_first>
    - `l2scanner/__main__.py` linhas 154-181 (`montar_despachante`) — O MOLDE do aviso alto de D-02: tenta, degrada com WARNING, devolve None, e o scanner sobe.
    - `l2scanner/__main__.py` linhas 874-935 (o inicio do `laco_principal`: os tres caminhos de fonte, o `extras = {"hp_proprio": ...}` da linha 897 e o WARNING do `hp_proprio` sem `--janela`) — onde a regiao entra.
    - `l2scanner/__main__.py` linhas 829-862 (`comando_teste_de_agenda`) — o molde de um comando de conferencia que monta o que precisa, faz uma coisa e sai.
    - `l2scanner/__main__.py` linhas 1251-1316 (o fim do `main`: as flags, a ordem dos despachos, a carga da calibracao e a resolucao do `--janela AUTO`) — onde a flag nova entra e por que ela entra DEPOIS da calibracao.
    - `.planning/quick/260825-bmw-calibrar-a-imagem-de-conferencia-nao-era/260825-bmw-SUMMARY.md` — a licao do `cv2.imwrite` devolvendo False em silencio quando o arquivo esta travado por um visualizador aberto. Este task repete o mesmo padrao de gravacao e nao pode repetir o mesmo defeito.
  </read_first>
  <behavior>
    Em `tests/test_manutencao.py`, classe `TestMontagemNoArranque` — a decisao
    de ligar ou nao o recurso e logica, e logica precisa de teste mesmo morando
    no `__main__`:

    - **sem OCR disponivel, devolve None e avisa em WARNING (D-02).**
      `monkeypatch` em `ocr.disponivel` para False; afirme que
      `montar_vigia_de_manutencao(<regiao>)` devolve None e que houve um registro
      de nivel WARNING (use `caplog`). Silencio aqui seria o pior desfecho: o
      usuario acharia que esta coberto.
    - **sem regiao, devolve None (D-07).** `montar_vigia_de_manutencao(None)` e
      None, mesmo com o OCR disponivel.
    - **com OCR e regiao, devolve um `VigiaDeManutencao`.** E o `ler_texto` dele
      e `ocr.ler_texto`, nao outra coisa.

    Nao escreva teste para o `--testar-manutencao`: ele existe justamente para o
    que a suite nao alcanca (a fonte do jogo, numa manutencao real). A
    conferencia dele e humana e esta em `<verification>`.
  </behavior>
  <action>
    **`l2scanner/__main__.py`**:

    - `montar_vigia_de_manutencao(regiao) -> VigiaDeManutencao | None`, ao lado
      de `montar_relogio` e no mesmo formato: nunca levanta, degrada com log e
      deixa o scanner subir. Sem regiao: `log.info` explicando que o recurso
      pede `--janela` ou a chave `banner_manutencao` no `calibration.json`. Sem
      OCR: `log.warning` em duas linhas, com o motivo vindo de
      `ocr.motivo_indisponivel()` e a frase de que o resto do scanner continua
      igual — o mesmo tom do aviso de entrega desativada. Com os dois:
      `log.info` dizendo que o aviso de manutencao esta ativo e em qual regiao.
    - Em `laco_principal`, ANTES do bloco que escolhe a fonte: calcule
      `regiao_banner = cal.regiao_do_banner(na_janela=bool(args.janela))` e
      `vigia_manutencao = montar_vigia_de_manutencao(regiao_banner)`. Em
      `--replay`, nao monte o vigia: uma sessao gravada nao tem o banner e os
      horarios do arquivo ancorariam um instante que nunca existiu. Diga isso
      numa linha de log e numa linha de comentario.
    - Monte o dicionario de `extras` UMA vez, antes dos tres caminhos, com
      `hp_proprio` (como hoje) e `banner_manutencao` quando o vigia existe.
      Passe `extras` tambem para o `MssSource` — hoje ele e construido sem
      extras, e D-07 permite explicitamente o caminho `mss` COM a regiao
      configurada. Nao acrescente o extra quando o vigia e None: no caminho
      `mss` cada extra custa uma captura propria por tick.
    - Passe `manutencao=vigia_manutencao` na construcao da `Sessao`. Os textos
      ja aparecem no console de graca, porque o laco ja itera
      `resultado.avisos` e chama `destacar`.
    - Flag `--testar-manutencao` (dest `testar_manutencao`, `action="store_true"`),
      com help dizendo que ela captura a janela agora e mostra o que o OCR le no
      banner. O despacho dela NAO pode ficar junto de `--testar-agenda`:
      diferente da agenda, esta ferramenta precisa da calibracao e da janela
      resolvida. Ela entra logo ANTES da chamada a `laco_principal`, recebendo
      `cal`.
    - `comando_testar_manutencao(args, cal) -> int` (D-13). Nesta ordem:
      1. Resolve `regiao = cal.regiao_do_banner(na_janela=bool(args.janela))`.
         None: imprime que o recurso esta desligado neste modo, diz para rodar
         com `--janela` ou configurar `banner_manutencao`, e devolve 2.
      2. Imprime a regiao E DE ONDE ELA VEIO — calibrada ou padrao derivado da
         party window. Sem essa frase o usuario nao sabe qual dos dois esta
         conferindo.
      3. Monta o `JanelaSource` com `extras={"banner_manutencao": regiao}` e
         captura um frame. Se `frame.extras` nao tiver o recorte, explica que a
         regiao caiu FORA da janela (foi isso que `_extra_para_janela` decidiu),
         imprime a regiao e o tamanho do frame completo, e devolve 2.
      4. Grava o recorte em `PASTA_LOGS` com nome carimbado pelo horario
         (`banner-manutencao-HHMMSS.png`) e **confere o retorno do
         `cv2.imwrite`** — False significa que nada foi gravado, e nesse caso
         diga isso em vez de anunciar um caminho que nao existe. Imprima o
         caminho ABSOLUTO e o horario. E a licao literal da tarefa 260825-bmw.
      5. Chama `ocr.ler_texto(recorte)`. None: imprime
         `ocr.motivo_indisponivel()` e devolve 1. Senao imprime o texto CRU
         entre delimitadores visiveis (espaco em branco importa aqui).
      6. Imprime o veredito do parser: `eh_banner_de_manutencao`,
         `interpretar_banner` e, quando ha duracao, o momento implicado
         (`montar_relogio(args).agora() + duracao`) formatado como o usuario le
         no relogio. Devolve 0.
      Feche a fonte no `finally`.

    **`requirements.txt`** (D-12): acrescente os SEIS pacotes, com um bloco de
    comentario no estilo do arquivo — que justifica cada dependencia, nao apenas
    a lista. O comentario precisa dizer: que o motor de OCR ja vem no Windows 11
    (zero instalador, zero modelo para baixar); que sao seis pacotes porque as
    bindings do WinRT sao MODULARES desde set/2023 e faltar uma quebra no meio
    da cadeia de chamada, nao no import; e que sem elas o scanner sobe igual e
    so o aviso de manutencao se desliga (ver `l2scanner/ocr.py`).
    `winrt-Windows.Media.Ocr`, `winrt-Windows.Graphics.Imaging`,
    `winrt-Windows.Storage.Streams`, `winrt-Windows.Globalization`,
    `winrt-Windows.Foundation`, `winrt-Windows.Foundation.Collections`, todos
    `>=3.2.1` — as versoes que o spike instalou e exercitou. NAO acrescente
    nenhum outro pacote: em particular, nada de `winrt-ocr-python`, que a
    pesquisa de stack do projeto marca como mantenedor unico e sem release desde
    abril de 2025.

    **`vigiar-party.bat`** (D-12): o arquivo tem HOJE **dois** blocos identicos
    de checagem de dependencia. CONSOLIDE em UM SO — o primeiro, o que fica
    logo depois da criacao do `.venv` — e apague o segundo, preservando o
    comentario `REM --janela le a janela do jogo direto...` que vive colado nele
    e explica a linha de execucao. A linha de checagem que sobra passa a incluir
    o modulo de OCR, para que o `.venv` antigo do usuario se atualize sozinho na
    proxima vez que ele der dois cliques. Confira, alem do modulo de OCR, o de
    imagem — sao pacotes separados e faltar um so aparece no meio da chamada.
    Nao mexa em mais nada do `.bat`.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests -q && test "$(grep -v '^REM' vigiar-party.bat | grep -c 'Scripts.python.exe. -c .import')" = "1" && grep -q 'winrt' vigiar-party.bat && grep -q 'winrt-Windows.Media.Ocr' requirements.txt && test "$(grep -v '^#' l2scanner/calibracao.py | grep -c 'VERSAO_DO_ESQUEMA = 2')" = "1" && python -m l2scanner --help | grep -q 'testar-manutencao'</automated>
  </verify>
  <done>O arranque liga o recurso quando ha OCR e regiao, avisa alto quando falta OCR e cala com uma frase util quando falta regiao; `--testar-manutencao` aparece no `--help`; o `.bat` tem UM unico bloco de checagem, agora incluindo o OCR; o `requirements.txt` explica por que os seis pacotes existem; a suite inteira segue verde.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| tela do jogo -> recorte -> OCR | Texto que outros JOGADORES escrevem (chat, nomes, macros) pode cair dentro do recorte e virar entrada do parser. E a unica entrada nao confiavel deste recurso. |
| processo do scanner -> Chatwoot/WhatsApp | O que o parser concluir vira mensagem no celular de toda a party. Um falso positivo custa o farm do grupo. |
| PyPI -> `.venv` do usuario | Seis pacotes novos entram na arvore de dependencias. |
| processo do scanner -> `logs/*.png` | O recorte gravado pelo `--testar-manutencao` e um pedaco da tela do usuario. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-onz-01 | Spoofing | `manutencao.eh_banner_de_manutencao` / a regiao do recorte | medium | mitigate | Um jogador que escreva "Server Maintenance 5 minutes" no chat forjaria um alerta e faria o grupo largar o farm. Tres portas em serie: (1) a regiao e derivada da PARTY WINDOW, nunca da janela inteira nem da caixa de chat — e por isso que `regiao_do_banner` parte de `party_window_na_janela` e nao do frame completo; (2) exige a raiz `mainten` E uma duracao interpretavel; (3) exige o CONSENSO de duas leituras (D-05). Residual aceito: quem mantiver a frase na tela por duas cadencias ainda forja um aviso — raio de estrago de uma mensagem, dentro do ASVS L1. |
| T-onz-02 | Denial of Service | `ocr.ler_texto` dentro do tick de captura | high | mitigate | Uma excecao ou uma chamada cara de OCR no tick para o scanner de olhar a party, e a proxima morte real passa despercebida — o pior modo de falha declarado no roadmap. Mitigacao: `ler_texto` NUNCA levanta (`except Exception -> None`), o `VigiaDeManutencao._ler` repete a guarda, a cadencia de 5 s (D-06) limita a ~0,2 Hz, o recorte e pequeno, e a ancora (D-04) torna o aviso de 5 minutos independente de qualquer leitura futura. |
| T-onz-03 | Tampering | instalacao pip dos seis pacotes `winrt-*` | high | mitigate | Legitimidade resolvida por evidencia, nao por suposicao: sao as projecoes oficiais do Windows SDK nomeadas com versao e fonte na tabela de stack do proprio projeto (`.claude/CLAUDE.md`, `winrt-*` 3.2.1, fonte `libraries.io/pypi/winrt-Windows.Media.Ocr`), ja instaladas e exercitadas no `.venv` pelo spike aprovado. Mitigacao: versoes fixadas nas do spike, lista fechada de seis, proibicao explicita de `winrt-ocr-python` no Task 4, e conferencia humana do que o `pip install` acrescentou (ver `<verification>` item 5). |
| T-onz-04 | Information disclosure | `logs/banner-manutencao-*.png` | low | accept | O recorte contem um pedaco da tela do usuario. Aceito: `logs/` e `*.png` ja estao no `.gitignore`, o arquivo nunca sai da maquina, e o projeto ja grava mais que isso em `recordings/` e no `scanner.log` (que tem os nomes dos membros). |
| T-onz-05 | Repudiation | marcador em `.agenda/` | low | accept | Se o disco falhar no `marcar`, o `RegistroEmDisco` devolve True e o aviso pode sair em dobro. Comportamento existente e deliberado ("preferir o aviso duplicado ao aviso perdido"); este recurso herda a mesma escolha, pela mesma razao: manutencao que ninguem soube e pior que manutencao anunciada duas vezes. |
</threat_model>

<verification>
1. `python -m pytest -q` — a suite inteira verde (634+ testes), sem jogo aberto,
   sem rede e **sem as bindings de OCR** no Python que roda os testes. Este
   ultimo detalhe e o teste de D-02 mais forte que existe.
2. `python -m pytest tests/test_manutencao.py -q -k "Consenso or Ancora or Expiracao"`
   — os testes que o usuario pediu nominalmente, isolados, para ler os nomes e
   conferir que a lista dele esta coberta item a item.
3. Leitura do diff em `l2scanner/manutencao.py`: confirmar que o passo que monta
   os avisos a partir da ancora roda TAMBEM nos ticks sem leitura. E a unica
   linha onde D-10 pode ser perdida sem nenhum teste ficar vermelho por acidente.
4. `git diff --name-only | grep -E 'visao\.py|rastreador\.py|identidade\.py'` —
   tem que sair VAZIO. Este recurso e ortogonal a deteccao de party.
5. <human-check>Conferencia humana, no fim: (a) rodar `vigiar-party.bat` uma vez
   e ver o `.venv` se atualizar sozinho, com o arranque dizendo se o aviso de
   manutencao ligou ou por que nao; (b) conferir que o `pip install` acrescentou
   somente pacotes `winrt-*` (T-onz-03); (c) rodar
   `vigiar-party.bat --testar-manutencao` com o jogo aberto, abrir o PNG salvo e
   verificar se o recorte pega o lugar onde o banner aparece — se nao pegar, a
   correcao e a chave `banner_manutencao` no `calibration.json`, sem tocar em
   codigo; (d) na PROXIMA MANUTENCAO REAL, rodar `--testar-manutencao` com o
   banner na tela e comparar o texto lido com o texto da tela. So esse ultimo
   passo prova o que o spike nao provou: a precisao do OCR na fonte do jogo.</human-check>
</verification>

<success_criteria>
- O banner na tela produz UM aviso no WhatsApp com o tempo como esta na tela e a
  hora em que o servidor cai.
- Faltando ate 5 minutos, sai o SEGUNDO aviso — pelo relogio ancorado, mesmo
  sem o banner na tela.
- Uma leitura discrepante entre duas boas nao anuncia nada.
- `You cannot use this item because the server will restart in a few minutes`
  nao vira manutencao.
- O typo `Maintence` e a grafia `Maintenance` valem igualmente.
- Cada aviso sai uma vez so, inclusive com as duas instancias do usuario.
- Os marcadores tem a data na frente e o `podar()` os remove em 3 dias.
- A ancora expira depois da manutencao sem reavisar e sem bloquear a proxima.
- Sem as bindings de OCR, o recurso se desliga, o arranque avisa alto e nada
  mais muda.
- Os dois avisos atravessam o silencio de TvT/Prime, moldurados.
- `--testar-manutencao` mostra a regiao, salva o recorte, imprime o texto cru e
  o veredito do parser.
- A calibracao real do usuario continua carregando (esquema segue v2).
- Nenhuma linha alterada em `visao.py`, `rastreador.py` ou `identidade.py`.
- 634+ testes passando.
</success_criteria>

<output>
Create `.planning/quick/260825-onz-aviso-de-manutencao-do-servidor-lendo-o-/260825-onz-SUMMARY.md` when done
</output>
