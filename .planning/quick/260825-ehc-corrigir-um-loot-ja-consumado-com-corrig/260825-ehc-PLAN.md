---
phase: quick-260825-ehc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/loot.py
  - l2scanner/comandos.py
  - l2scanner/__main__.py
  - tests/test_loot.py
  - tests/test_comandos.py
autonomous: true
requirements: [QUICK-260825-ehc]

estimate:
  tokens: 70000
  raw_tokens: 35000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`.corrigir-<nick>` troca o DONO do loot ja consumado mais recente, e o `.<nick>` reflete a troca nos DOIS lados: o antigo perde um loot, o novo ganha um (D-01, D-02)."
    - "A forma de duas palavras `.corrigir <nick>` faz exatamente a mesma coisa que a forma com hifen — nao e opcional (D-01). Sem ela, `.corrigir kaus` morreria em silencio e o usuario acharia que corrigiu."
    - "`.corrigir` SOZINHO, sem nick, nao faz nada e nao pode ser lido como consulta de um personagem chamado 'corrigir' (D-01)."
    - "So o registro MAIS RECENTE e tocado: com dois bosses ja consumados, o mais antigo fica intacto (D-02). O raio de estrago e limitado por desenho, nao por cuidado."
    - "A resposta NOMEIA exatamente o que mudou — o boss, o horario, de quem era e para quem foi (D-03). E a unica rede de seguranca do usuario contra ter corrigido o registro errado quando outro boss passou no meio tempo."
    - "A troca CRIA o `pegou_` novo ANTES de apagar o velho (D-04). Falha no criar: nada muda. Falha no apagar: sobra duplicado visivel e consertavel. A ordem inversa perderia o loot em silencio."
    - "Corrigir para o MESMO apelido do dono atual e no-op puro e NAO apaga nada (D-05) — o registro sobrevive. Sem a guarda, o `_criar` devolveria 'ja_existia' e o passo de apagar destruiria o unico registro que existia."
    - "Depois de qualquer chamada a `corrigir` — corrigida, no-op, sem registro ou falha de disco — ainda existe um `pegou_` para aquele alvo. A estatistica nunca encolhe."
    - "Sem nenhum registro na pasta, `.corrigir-<nick>` responde com honestidade e NAO levanta (D-06)."
    - "O nick corrigido vira conhecido (marcador `nick_*`), senao o `.<nick>` dele nao responderia (D-07)."
    - "A resposta sai so na conversa de origem, sem eco no grupo (D-08), igual aos outros comandos de loot."
    - "A suite inteira segue verde (581+ testes), sem o jogo aberto e sem rede."
  artifacts:
    - "l2scanner/loot.py — dataclass `Correcao`, `RegistroDeLoot.corrigir()` e `responder_correcao()`"
    - "l2scanner/comandos.py — `Comando.LOOT_CORRIGIR` e os dois ramos de `.corrigir` em `interpretar_dinamico`"
    - "l2scanner/__main__.py — ramo `Comando.LOOT_CORRIGIR` em `atender_comandos`, com `avisar_o_grupo=False`"
    - "tests/test_loot.py — a troca nos dois lados, a guarda do mesmo nick, o registro mais antigo intacto, a invariante do alvo, a falha de disco"
    - "tests/test_comandos.py — as duas sintaxes que corrigem, as que nao corrigem, e a correcao na costura"
  key_links:
    - "`corrigir()` -> `_criar` -> `unlink`: a ORDEM e o link critico (D-04). Inverter perde o loot em silencio numa estatistica que o projeto trata como 'para sempre'."
    - "`apelido(nick) == anterior` -> retorno antecipado (D-05): a guarda e o unico ponto entre um no-op e a destruicao do registro. Sem ela o caminho de sucesso apaga o arquivo que acabou de nao criar."
    - "`interpretar_dinamico` -> ramo `crua.lower() == \"corrigir\"` com `return None` explicito: e o `return` que impede `.corrigir` sozinho de cair no ramo de consulta e virar `.{nick}`."
    - "`corrigir()` -> `_criar(nick_*)` (D-07): sem esse marcador o `.<nick>` do novo dono nao responde, e a correcao ficaria invisivel exatamente para quem foi corrigido."
    - "`atender_comandos` -> `responder_correcao`: o dispatch e o unico ponto onde o comando vira acao; sem ele o parser reconhece e nada acontece."
---

<objective>
Dar ao usuario um jeito de corrigir, pelo WhatsApp, um loot de Solo Boss JA
CONSUMADO.

O caso real: o boss das 10:00 passou, a designacao era do TioMad, entao o
`consumir()` gravou `pegou_2026-08-25-1000_tiomad`. So que quem pegou de
verdade foi o Kaus. Hoje NAO HA caminho nenhum pelo WhatsApp — o `cancelar()`
recem-criado nao encosta nos `pegou_*` de proposito (cancelar e sobre a VEZ,
nao sobre o historico), e a unica saida e renomear o arquivo em `.loot/` a mao.

Purpose: a estatistica de loot e o unico estado deste projeto que nunca e
podado — "quantos loots o J4guar pegou" e uma pergunta sobre meses. Um registro
errado que so se conserta abrindo o Explorer nao e um registro confiavel.

Output: `Comando.LOOT_CORRIGIR`, `RegistroDeLoot.corrigir()`,
`responder_correcao()`, o dispatch em `atender_comandos`, e os testes que
provam que a troca aparece nos dois lados do `.<nick>` sem nunca perder um loot.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

@l2scanner/loot.py
@l2scanner/comandos.py
</context>

<decisions_travadas>
Decisoes do usuario. NAO revisitar, NAO propor alternativa, NAO simplificar.

- **D-01** — Comando `.corrigir-<nick>`, mais a forma de duas palavras
  `.corrigir <nick>`. Novo `Comando.LOOT_CORRIGIR`. A forma de duas palavras
  NAO e opcional: o bug encontrado na tarefa anterior (`.loot cancelar`
  designava um personagem chamado "cancelar") mostrou que tratar so o ramo do
  hifen deixa a porta dos fundos aberta.
- **D-02** — Corrige SOMENTE o registro MAIS RECENTE (maior `alvo` entre
  `registros()`). Nunca historico arbitrario — raio de estrago limitado por
  desenho.
- **D-03** — A resposta NOMEIA exatamente o que mudou: "O loot do Solo Boss das
  10:00 passou do TioMad para o Kaus." Esse texto NAO e cosmetico — e a unica
  rede de seguranca do usuario contra ter corrigido o registro errado quando
  outro boss ja passou no meio tempo. Documente isso na docstring.
- **D-04** — ORDEM OBRIGATORIA na troca: CRIAR o `pegou_` novo ANTES de apagar
  o velho. Se o criar falhar: nada mudou, o registro velho continua la. Se o
  apagar falhar: sobra registro DUPLICADO, que e visivel no `.<nick>` e
  consertavel. A ordem inversa PERDE o loot em silencio, que e o pior desfecho
  possivel numa estatistica que o projeto trata como "para sempre".
- **D-05** — GUARDA CRITICA, e o bug mais facil de escrever aqui: se o nick
  novo tem o MESMO `apelido()` do dono atual, e no-op puro e NAO pode apagar
  nada. Sem essa guarda o `_criar` devolve "ja_existia" (mesmo nome de arquivo)
  e o passo de apagar destruiria o unico registro que existia. Precisa de teste
  dedicado.
- **D-06** — Sem nenhum registro na pasta: responde com honestidade e NAO
  levanta.
- **D-07** — O nick corrigido vira conhecido (marcador `nick_*`), senao o
  `.<nick>` dele nao responderia.
- **D-08** — Dispatch em `atender_comandos` do `__main__.py` com
  `avisar_o_grupo=False`, igual aos outros comandos de loot.

**Discricao do Claude, derivada de D-03** — o horario sai por
`descrever_momento(alvo, agora)`, que ja existe e ja e usado pelo
`responder_consulta`. Isso produz "de hoje as 10:00", "de ontem as 22:00", "de
23/08 as 14:00" em vez de so "das 10:00". E estritamente MAIS rede de
seguranca, nao menos: D-03 existe para o usuario perceber que corrigiu o
registro errado, e o dia e justamente a informacao que falta quando o registro
errado e o de ontem. Nao invente um formatador novo.

**Limitacao ACEITA e que precisa ficar documentada no codigo** — o nome do dono
ANTIGO sai do nome do arquivo, e o nome do arquivo guarda o `apelido()`
(minusculo). Entao a resposta diz "Tiomad", nao "TioMad". Isso e honesto: o
slug e o unico registro que existe do dono antigo. NAO tente restaurar a
caixa original com heuristica, e escreva o porque numa linha de comentario.
Os testes assertam a forma slug-cased, nao a original.

**Fora de escopo:** o `cancelar()` continua sem encostar em `pegou_*`, e
`.corrigir` continua sem encostar em `proximo.json`. Sao dois comandos sobre
duas coisas diferentes — a VEZ e o HISTORICO — e misturar os dois foi
explicitamente rejeitado na tarefa anterior.
</decisions_travadas>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: o caminho inteiro do `.corrigir-<nick>`, de ponta a ponta</name>
  <files>tests/test_loot.py, tests/test_comandos.py, l2scanner/loot.py, l2scanner/comandos.py, l2scanner/__main__.py</files>
  <read_first>
    - `l2scanner/loot.py` linhas 108-172 (`_criar`, `_nome_do_pegou`, `registrar`, `registros`, `resumo`) — as primitivas exatas que `corrigir` compoe; o tri-estado do `_criar` e o motor de D-04.
    - `l2scanner/loot.py` linhas 243-288 (`cancelar`, `nicks_conhecidos`) — o estilo de docstring "duas coisas que parecem detalhe e nao sao" que este task espelha, e o `_criar(nick_*)` de D-07.
    - `l2scanner/loot.py` linhas 294-307 (`descrever_momento`) e 388-429 (`responder_cancelamento`) — o formatador de horario e o molde exato de uma funcao `responder_*`.
    - `l2scanner/comandos.py` linhas 219-280 (`interpretar_dinamico`) — os ramos `loot-` e `loot` que o `.corrigir` copia.
    - `l2scanner/__main__.py` linhas 58-65 (os imports de `loot`) e 503-530 (os tres ramos de loot em `atender_comandos`).
    - `tests/test_comandos.py` linhas 665-760 (`TestLootNaCostura`) — o `LeitorFalso` e o helper `_atender` que a costura reusa.
  </read_first>
  <behavior>
    RED primeiro. Escreva estes dois testes, veja falhar, so entao implemente.

    Em `tests/test_loot.py`, numa classe nova `TestCorrecao` depois de
    `TestCancelamento`:

    - **a troca aparece nos DOIS lados.** Registre `pegou_` para "TioMad" no
      boss das 10:00. Chame `responder_correcao(registro, [solo_boss], em(10, 30), "Kaus")`.
      Afirme: `registro.resumo("TioMad")` volta a `(0, None)`, `registro.resumo("Kaus")`
      vira `(1, em(10, 0))`, e a resposta contem "Tiomad", "Kaus" e "10:00".
      O total de registros continua 1. Este e o teste que prova D-01+D-02+D-03
      de uma vez.

    - **a guarda do mesmo nick nao apaga nada (D-05).** Registre `pegou_` para
      "TioMad" no boss das 10:00. Chame `registro.corrigir("TIOMAD")` — caixa
      diferente, MESMO `apelido()`. Afirme que `registro.resumo("TioMad")`
      continua `(1, em(10, 0))` e que `registros()` continua com um elemento.
      Este e o teste que o usuario pediu nominalmente; ele falha de forma
      DESTRUTIVA se a guarda faltar, entao rode-o antes e depois.

    Em `tests/test_comandos.py`, dentro de `TestLootNaCostura` — o teste que
    prova a costura, que e onde os erros deste projeto moram:

    - **`.corrigir-kaus` atravessa parser, dispatch e disco.** Crie um
      `RegistroDeLoot(tmp_path / "loot")`, registre `pegou_` para "tiomad" no
      boss das 08:00, chame `self._atender(tmp_path, ".corrigir-kaus", loot)`.
      Afirme que os destinos sao so `["1"]` (sem eco no grupo, D-08), que a
      resposta contem "Kaus", e que `loot.resumo("kaus")[0] == 1`.
  </behavior>
  <action>
    Implemente o caminho fino inteiro — registro, texto, parser e dispatch —
    numa passada so, para que o `.corrigir-<nick>` funcione de ponta a ponta
    antes de qualquer variacao de sintaxe entrar.

    **`l2scanner/loot.py` — dataclass `Correcao`**: frozen, ao lado de
    `Designacao`. Campos: `estado: str` (`"corrigido"` | `"mesmo_dono"` |
    `"sem_registro"` | `"falhou"`), `anterior: str = ""` (o SLUG do dono
    antigo), `novo: str = ""` (o nick novo, como foi digitado), `alvo: datetime | None = None`.
    Docstring explicando por que o estado e uma string tri-estado-e-meia e nao
    um booleano: e o mesmo motivo do `_criar` logo acima — a resposta precisa
    distinguir "trocou" de "ja era dele" de "nao tinha nada" de "o disco
    falhou", e colapsar qualquer par desses faria o bot mentir sobre o que
    acabou de acontecer com a estatistica.

    **`l2scanner/loot.py` — `RegistroDeLoot.corrigir(nick) -> Correcao`**:
    metodo novo logo depois de `cancelar`. NUNCA levanta, NUNCA devolve None.
    Passos, nesta ordem exata:

    1. `achados = self.registros()`; vazio devolve `Correcao("sem_registro", novo=nick)` (D-06).
    2. `anterior, alvo = max(achados, key=lambda par: (par[1], par[0]))` — o
       mais recente (D-02), com desempate deterministico pelo slug para que
       duas chamadas seguidas escolham o mesmo registro quando um duplicado
       existir.
    3. **A GUARDA (D-05)**: `if apelido(nick) == anterior:` devolve
       `Correcao("mesmo_dono", anterior=anterior, novo=nick, alvo=alvo)` sem
       tocar em disco.
    4. `estado = self._criar(self._nome_do_pegou(nick, alvo))` — CRIAR ANTES
       (D-04). `"falhou"` devolve `Correcao("falhou", ...)` sem apagar nada.
    5. So agora apaga o velho: `(self._pasta / self._nome_do_pegou(anterior, alvo)).unlink(missing_ok=True)`,
       dentro de um `try/except OSError` que segue em frente. `apelido()` e
       idempotente sobre um slug, entao `_nome_do_pegou` reconstroi o nome do
       arquivo velho sem precisar de formatador novo.
    6. `self._criar(f"{_PREFIXO_NICK}{apelido(nick)}")` (D-07), idempotente.
    7. Devolve `Correcao("corrigido", anterior=anterior, novo=nick, alvo=alvo)`.

    A docstring precisa dizer o PORQUE de tres coisas, no estilo do modulo:
    (1) a ordem criar-antes-de-apagar de D-04, com os tres desfechos escritos
    (nada muda / duplicado consertavel / loot perdido em silencio) e a frase de
    que a ordem inversa e o pior desfecho possivel; (2) a guarda de D-05, com o
    mecanismo explicito — mesmo apelido gera o MESMO nome de arquivo, o `_criar`
    devolveria "ja_existia" e o passo 5 apagaria o unico registro que existia;
    (3) por que so o mais recente (D-02) — o raio de estrago e limitado por
    desenho, e corrigir historico arbitrario nao e uma funcionalidade que
    alguem pediu.

    Um `estado == "ja_existia"` no passo 4 segue para o passo 5 de proposito:
    ele so acontece quando o alvo tinha DOIS donos registrados (o duplicado que
    D-04 aceita deixar para tras), e apagar o velho ali e o conserto, nao a
    perda. Escreva isso em uma linha de comentario.

    **`l2scanner/loot.py` — `responder_correcao(registro, eventos, agora, nick) -> str`**:
    funcao pura no fim do arquivo, depois de `responder_cancelamento`, mesma
    assinatura-molde e tempo por parametro. Chama `registro.corrigir(nick)` e
    traduz o `estado` em texto. O nome do evento sai de `eventos` pelo mesmo
    `eh_solo_boss` que as outras duas usam, com "Solo Boss" como recurso. O
    horario sai de `descrever_momento(correcao.alvo, agora)`.

    - `"corrigido"`: `f"O loot do {nome} de {momento} passou do {exibir(anterior)} para o {exibir(novo)}."`
    - `"mesmo_dono"`: diz que o loot daquele boss JA era dele e que nada mudou.
    - `"sem_registro"`: diz que nao ha nenhum loot daquele evento registrado
      para corrigir.
    - `"falhou"`: diz que nao conseguiu gravar e que o loot continua com o dono
      antigo — nomeando os dois, porque uma falha silenciosa aqui e
      indistinguivel de sucesso.

    A docstring precisa registrar D-03 com todas as letras: o texto NAO e
    cosmetico, e a unica rede de seguranca do usuario contra ter corrigido o
    registro errado quando outro boss ja passou no meio tempo — por isso ele
    nomeia o boss, o momento, o dono antigo e o novo, e nao um "pronto" seco.
    Registre tambem, em uma linha, a limitacao aceita: o dono antigo sai
    slug-cased porque o nome do arquivo e o unico registro que existe dele.

    **`l2scanner/comandos.py` — `Comando.LOOT_CORRIGIR = "loot_corrigir"`**:
    novo membro do enum junto dos outros de loot, com comentario dizendo que
    ele e o unico comando que reescreve HISTORICO (os outros mexem na vez), e
    que por isso o alcance dele para no registro mais recente.

    **`l2scanner/comandos.py` — o ramo com hifen em `interpretar_dinamico`**:
    depois dos ramos de `loot`, `if crua.lower().startswith("corrigir-"):`
    extrai o nick, devolve `(Comando.LOOT_CORRIGIR, nick)` quando
    `_NICK_VALIDO.fullmatch(nick)` casa, e `None` caso contrario. Sem palavras
    reservadas aqui: `.corrigir` nao tem forma destrutiva sem argumento, entao
    nao existe a colisao que obrigou o `_PALAVRAS_DE_CANCELAMENTO` a nascer.

    **`l2scanner/__main__.py`**: importe `responder_correcao` do `.loot` e
    acrescente o ramo `elif pedido.comando is Comando.LOOT_CORRIGIR:` junto dos
    outros tres, com o mesmo guarda-chuva `if loot is None` e
    `avisar_o_grupo = False` (D-08). O comentario do ramo deve dizer o porque
    PROPRIO dele, nao "igual ao de cima": corrigir historico e conserto de
    contabilidade entre quem sabe o que aconteceu, e anunciar no grupo que o
    loot mudou de dono convidaria a discussao que o registro existe para
    encerrar.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_loot.py tests/test_comandos.py -q</automated>
  </verify>
  <done>`.corrigir-kaus` atravessa parser, dispatch, disco e resposta: o `.<nick>` do antigo perde o loot, o do novo ganha, a resposta nomeia os dois e o horario, e corrigir para o mesmo apelido nao apaga nada.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: as invariantes que protegem a estatistica</name>
  <files>tests/test_loot.py, l2scanner/loot.py</files>
  <read_first>
    - `tests/test_loot.py` linhas 123-138 (`test_falha_de_disco_MANTEM_a_designacao`) — o padrao de `monkeypatch` sobre `_criar` que este task reusa para simular disco cheio.
    - `l2scanner/loot.py` — o `corrigir` e o `responder_correcao` escritos no Task 1.
  </read_first>
  <behavior>
    Dois destes testes DEVEM falhar antes da implementacao (as respostas de
    `"mesmo_dono"` e `"falhou"` ainda nao existem como texto). Os outros podem
    passar de primeira, porque o Task 1 ja implementou o mecanismo — isso e
    esperado e NAO e desculpa para pular nenhum: eles sao a armadura contra a
    regressao, e a propriedade que o usuario chamou de "invariante que protege
    a estatistica" precisa de um teste com nome proprio para sobreviver ao
    proximo refactor.

    Em `tests/test_loot.py`, na classe `TestCorrecao`:

    - **so o registro MAIS RECENTE e tocado (D-02).** Registre dois `pegou_`
      para "TioMad": um no boss das 08:00 e outro no das 10:00. Corrija para
      "Kaus". Afirme que o das 10:00 virou de Kaus e que o das 08:00 continua
      do TioMad — `resumo("TioMad")` fica `(1, em(8, 0))` e `resumo("Kaus")`
      fica `(1, em(10, 0))`.

    - **o total nunca DIMINUI numa correcao bem sucedida.** Com um registro
      unico no alvo, `len(registros())` antes e depois da correcao e o mesmo.

    - **sobra sempre um `pegou_` para aquele alvo, em TODOS os desfechos.**
      Escreva um teste que roda os quatro estados (corrigido, mesmo_dono,
      sem_registro quando nao ha alvo nenhum, e falhou com `_criar`
      monkeypatchado para devolver `"falhou"`) e afirma, em cada um que tinha
      registro, que ainda existe algum `(slug, alvo)` com aquele `alvo` em
      `registros()`. Esta e a forma sempre-verdadeira da invariante: o dono
      pode mudar, o loot nunca some.

    - **falha de disco NAO apaga o velho (D-04).** `monkeypatch` em
      `RegistroDeLoot._criar` devolvendo `"falhou"`. Afirme que
      `corrigir("Kaus").estado == "falhou"`, que `resumo("TioMad")` continua
      `(1, ...)` e que "Kaus" continua com zero.

    - **sem nenhum registro nao levanta e responde honesto (D-06).** Pasta
      vazia: `responder_correcao(...)` devolve texto contendo "corrigir" ou
      "registrado" (assere pela frase que voce escrever) e `registros()`
      continua vazio.

    - **o duplicado colapsa (o outro lado de D-04).** Registre `pegou_` para
      "tiomad" E para "kaus" no MESMO boss das 10:00 — o estado que sobra
      quando um apagar falhou. Corrija para "Kaus". Afirme que sobra
      exatamente um registro naquele alvo e que ele e do Kaus. Comente no
      teste que isto e o conserto do duplicado, nao perda de loot.

    - **a resposta do no-op nao mente.** `responder_correcao` com o mesmo
      apelido do dono atual devolve um texto que diz que ja era dele e que
      nada mudou — nunca o texto de "passou de X para Y".
  </behavior>
  <action>
    Complete `responder_correcao` com os ramos `"mesmo_dono"` e `"falhou"` se
    o Task 1 os tiver deixado como esboco, e ajuste o texto ate os testes
    passarem sem afrouxar nenhuma assercao.

    Se algum teste desta lista revelar um furo no `corrigir` do Task 1
    (ordem, guarda ou selecao do mais recente), conserte o `corrigir` — nao o
    teste. Estes seis testes sao a especificacao; o codigo do Task 1 e a
    tentativa.

    Nao acrescente parametro novo, nao troque a assinatura de `corrigir` e nao
    introduza um caminho para corrigir registro arbitrario. D-02 e o limite do
    raio de estrago e ele nao se negocia porque um teste ficou mais dificil de
    montar.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_loot.py -q</automated>
  </verify>
  <done>Os quatro estados de `Correcao` tem teste proprio; a invariante "sempre sobra um `pegou_` para aquele alvo" tem teste com nome proprio; falha de disco e duplicado tem comportamento provado.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: a porta dos fundos — `.corrigir <nick>` e `.corrigir` sozinho</name>
  <files>tests/test_comandos.py, l2scanner/comandos.py</files>
  <read_first>
    - `l2scanner/comandos.py` linhas 219-280 (`interpretar_dinamico`) — em especial o ramo `crua.lower() == "loot"` e o `return None` final dele, que e o molde exato deste task.
    - `tests/test_comandos.py` linhas 96-224 (`TestInterpretarDinamico`) — onde os testes entram, e os nomes que a classe ja usa.
  </read_first>
  <behavior>
    RED primeiro. Estes testes falham hoje porque o ramo de duas palavras nao
    existe.

    Em `tests/test_comandos.py`, dentro de `TestInterpretarDinamico`:

    - `.corrigir kaus` devolve `(Comando.LOOT_CORRIGIR, "kaus")` — a mesma
      coisa que `.corrigir-kaus`. Este e o teste que fecha a porta dos fundos
      de D-01.
    - `.CORRIGIR-Kaus` devolve `(Comando.LOOT_CORRIGIR, "Kaus")`: o comando e
      case-insensitive, o nick e preservado como digitado.
    - `.corrigir` SOZINHO devolve `None`. Com uma docstring dizendo o porque:
      comando sem argumento nao pode reescrever historico, e o `return None`
      explicito do ramo tambem e o que impede `.corrigir` de escorregar para o
      ramo de consulta e ser lido como um personagem chamado "corrigir".
    - `.corrigir` com `nicks_conhecidos=frozenset({"corrigir"})` continua
      devolvendo `None` — a prova direta de que o ramo fecha a porta mesmo
      quando existe um nick homonimo.
    - `.corrigir-a` e `.corrigir-j4;rm` devolvem `None`: o mesmo
      `_NICK_VALIDO` dos outros comandos, sem excecao.
    - Regressao: `.loot-j4guar`, `.loot-` e `.loot` continuam devolvendo
      exatamente o que devolviam. O comando novo nao pode ter deslocado
      nenhum ramo existente.
  </behavior>
  <action>
    Em `interpretar_dinamico`, logo depois do ramo `startswith("corrigir-")`
    criado no Task 1, acrescente o ramo de duas palavras
    `if crua.lower() == "corrigir":`, espelhando o ramo `== "loot"`: devolve
    `(Comando.LOOT_CORRIGIR, palavras[1])` quando ha segunda palavra e ela
    casa `_NICK_VALIDO`, e `return None` em qualquer outro caso.

    O `return None` no fim do ramo e obrigatorio e nao e redundancia: sem ele
    o fluxo cai no ramo de consulta logo abaixo, onde `_NICK_VALIDO` casa a
    palavra "corrigir" e um nick homonimo transformaria o comando em consulta.
    Escreva esse motivo em uma linha de comentario, e cite ao lado que este
    ramo existe por D-01 — porque tratar so o hifen foi exatamente o erro que
    fez `.loot cancelar` designar um personagem chamado "cancelar" na tarefa
    anterior.

    Nao acrescente "corrigir" ao `_VOCABULARIO` nem ao `_PALAVRA_HUMANA`: o
    vocabulario fixo tem precedencia sobre o dinamico, e por em `_VOCABULARIO`
    faria `interpretar` capturar `.corrigir` antes de `interpretar_dinamico`
    ver o argumento.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_comandos.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
  </verify>
  <done>As duas sintaxes de D-01 corrigem, `.corrigir` sozinho nao faz nada nem vira consulta, os ramos de `.loot` seguem intactos e a suite inteira esta verde.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WhatsApp -> Chatwoot -> `comandos_novos` | Texto de terceiro atravessa a rede e vira acao no scanner |
| `corrigir()` -> pasta `.loot/` | Estado duravel que NUNCA e podado e nao tem backup |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ehc-01 | Tampering | `.corrigir-<nick>` reescrevendo historico de loot de outra pessoa | high | mitigate | Passa pelo mesmo `comandos_novos` das quatro travas existentes: so `incoming`, nao `private`, dedupe por id e allowlist de telefone. Nenhum caminho novo de entrada e criado. |
| T-ehc-02 | Denial | Correcao em cadeia destruindo meses de estatistica | high | mitigate | D-02 limita o alcance ao registro MAIS RECENTE; nao existe sintaxe para atingir historico arbitrario. Cada `.corrigir` move um unico registro. |
| T-ehc-03 | Tampering | Perda silenciosa de um `pegou_` no meio da troca | critical | mitigate | D-04 (criar antes de apagar) + D-05 (guarda do mesmo apelido) + o teste de invariante do Task 2, que afirma que sobra um `pegou_` para o alvo nos quatro desfechos. |
| T-ehc-04 | Spoofing | Nick arbitrario virando dono de loot | medium | mitigate | `_NICK_VALIDO` ([A-Za-z0-9]{2,16}) no parser, o mesmo dos comandos de loot existentes. Sem shell, sem path traversal: o nick vira `apelido()` antes de tocar em nome de arquivo. |
| T-ehc-05 | Tampering | npm/pip/cargo installs | n/a | accept | Nenhuma dependencia nova. Somente stdlib e modulos ja no projeto. |
</threat_model>

<source_audit>
## Multi-Source Coverage Audit

| Fonte | Item | Plano | Task |
|-------|------|-------|------|
| CONTEXT | D-01 `.corrigir-<nick>` + `.corrigir <nick>` + `Comando.LOOT_CORRIGIR` | 01 | 1 (hifen) + 3 (duas palavras) |
| CONTEXT | D-02 so o registro mais recente | 01 | 1 (codigo) + 2 (teste dedicado) |
| CONTEXT | D-03 a resposta nomeia o que mudou, documentado na docstring | 01 | 1 |
| CONTEXT | D-04 criar antes de apagar | 01 | 1 (codigo) + 2 (falha de disco, duplicado) |
| CONTEXT | D-05 guarda do mesmo apelido, com teste dedicado | 01 | 1 |
| CONTEXT | D-06 sem registro: honesto, nao levanta | 01 | 1 (codigo) + 2 (teste) |
| CONTEXT | D-07 o nick corrigido vira conhecido (`nick_*`) | 01 | 1 |
| CONTEXT | D-08 dispatch com `avisar_o_grupo=False` | 01 | 1 |
| CONTEXT | Teste: a correcao muda de dono e o `.<nick>` reflete nos dois lados | 01 | 1 |
| CONTEXT | Teste: a guarda do mesmo nick nao apaga nada | 01 | 1 |
| CONTEXT | Teste: sem registro nao levanta e responde honesto | 01 | 2 |
| CONTEXT | Teste: o total nunca diminui numa correcao bem sucedida | 01 | 2 |
| CONTEXT | Teste: `.corrigir` sozinho nao faz nada | 01 | 3 |
| CONTEXT | Teste: so o registro mais recente e tocado | 01 | 2 |
| GOAL | Corrigir pelo WhatsApp um loot de Solo Boss ja consumado | 01 | 1-3 |

Nenhum item sem plano. Nenhum item adiado.
</source_audit>

<verification>
1. `python -m pytest -q` — a suite inteira verde, sem jogo aberto e sem rede.
2. `python -m pytest tests/test_loot.py -q -k Correcao` — os testes da correcao
   isolados, para ler os nomes e conferir que a lista de D-01..D-08 esta coberta.
3. Leitura do diff em `l2scanner/loot.py`: a linha do `unlink` vem DEPOIS da
   linha do `_criar`, e existe um retorno antecipado quando
   `apelido(nick) == anterior`. Sao as duas linhas onde este trabalho pode
   destruir dado.
</verification>

<success_criteria>
- `.corrigir-kaus` e `.corrigir kaus` trocam o dono do loot mais recente e a
  troca aparece nos dois lados do `.<nick>`.
- `.corrigir` sozinho nao faz nada, nem quando existe um nick "corrigir".
- Corrigir para o mesmo apelido nao apaga nada.
- Sobra sempre um `pegou_` para o alvo, nos quatro desfechos.
- Sem registro nenhum: resposta honesta, sem excecao.
- A resposta nomeia boss, momento, dono antigo e dono novo.
- Sai so na conversa de origem, sem eco no grupo.
- 581+ testes passando.
</success_criteria>

<output>
Create `.planning/quick/260825-ehc-corrigir-um-loot-ja-consumado-com-corrig/260825-ehc-SUMMARY.md` when done
</output>
