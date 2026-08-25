---
phase: quick-260825-cou
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/loot.py
  - l2scanner/comandos.py
  - l2scanner/agenda.py
  - l2scanner/sessao.py
  - l2scanner/__main__.py
  - tests/test_loot.py
  - tests/test_comandos.py
  - tests/test_agenda.py
  - tests/test_sessao.py
autonomous: true
requirements: [QUICK-260825-cou]

estimate:
  tokens: 80000
  raw_tokens: 40000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Gabriel manda `.loot-j4guar` no privado e recebe NA MESMA CONVERSA a confirmacao de que J4guar pega o loot do proximo Solo Boss, com o horario."
    - "O aviso de antecedencia do Solo Boss designado sai com o trecho 'Loot: J4guar' no fim; TvT e Prime nunca ganham essa linha, e o aviso AGORA tambem nao."
    - "Quando o horario do boss passa, o loot e registrado em disco EXATAMENTE UMA VEZ mesmo com as duas instancias rodando, e a designacao some — o aviso do boss seguinte sai sem 'Loot:'."
    - "`.j4guar` responde na conversa de origem: quantos loots o char pegou e quando foi o ultimo ('J4guar pegou 7 loots de Solo Boss. Ultimo: hoje as 10:00.')."
    - "`.palavra` com nick desconhecido e `.offline` recebem SILENCIO absoluto — o scanner nao responde lixo a qualquer palavra com ponto."
    - "O registro sobrevive a restart: arquivos em `.loot/`, que NUNCA sao podados (a poda de 3 dias do `.agenda/` nao alcanca as estatisticas)."
    - "O vocabulario fixo tem precedencia: `.status`, `.cancelar`, `.solo` etc. continuam exatamente como eram, e os 446+ testes existentes seguem verdes."
  artifacts:
    - "l2scanner/loot.py — RegistroDeLoot (pegou_*, nick_*, proximo.json), Designacao, nick_para_o_aviso, responder_designacao, responder_consulta, textos"
    - "tests/test_loot.py — registro atomico, consumo, corrida de duas instancias, textos, bordas"
    - "l2scanner/comandos.py — Comando.LOOT_DESIGNAR/LOOT_CONSULTA, MensagemDeComando.argumento, interpretar_dinamico, comandos_novos com nicks_conhecidos"
    - "l2scanner/agenda.py — texto_do_aviso(aviso, loot=None)"
    - "l2scanner/sessao.py — Sessao(loot=...), ResultadoDoTick.loot_consumado, injecao e consumo em _processar_agenda"
    - "l2scanner/__main__.py — PASTA_LOOT, dispatch dos dois comandos, fiacao nos dois lacos"
  key_links:
    - "comandos_novos -> interpretar_dinamico(nicks_conhecidos) -> RegistroDeLoot.nicks_conhecidos (o portao contra `.palavra` aleatoria)"
    - "atender_comandos -> responder_designacao -> proxima_ocorrencia([evento Solo Boss]) -> proximo.json (escrita atomica via os.replace)"
    - "Sessao._processar_agenda / laco_da_agenda -> nick_para_o_aviso(aviso, designacao) -> texto_do_aviso(aviso, loot=...)"
    - "Sessao._processar_agenda / laco_da_agenda -> RegistroDeLoot.consumir -> pegou_* com O_CREAT|O_EXCL (exatamente uma instancia registra)"
---

<objective>
Controle de loot do Solo Boss pelo WhatsApp: registrar quem pegou cada loot, consultar as
estatisticas de um char, e designar quem pega o proximo — com o nome do designado entrando
no aviso de antecedencia que a agenda ja manda.

O Solo Boss nasce de duas em duas horas (config.toml, 12 ocorrencias/dia) e a party reveza
quem fica com o loot. Hoje o revezamento e combinado de boca e ninguem lembra de quem e a
vez nem quantos cada um ja pegou. O scanner ja tem tudo em volta disso pronto: le comandos
do Chatwoot com allowlist de telefone, manda o aviso de antecedencia do boss, e sabe
sobreviver a restart e a duas instancias com marcadores atomicos em disco.

Purpose: a vez do loot vira registro duravel e consultavel, e o aviso que ja sai passa a
dizer de quem e a vez.
Output: `l2scanner/loot.py` novo + fiacao em `comandos.py`, `agenda.py`, `sessao.py` e
`__main__.py`, tudo com teste.
</objective>

<decisoes_ja_tomadas>
Fechadas no pedido. Nao reabrir, nao propor alternativa.

- **Quatro capacidades**: (1) registro duravel de quem pegou o loot de cada Solo Boss;
  (2) `.<nick>` responde total e ultimo loot NA CONVERSA DE ORIGEM; (3) `.loot-<nick>`
  designa o proximo, e o aviso de antecedencia ganha "Loot: X"; (4) quando a ocorrencia
  passa com designado, registra e CONSOME a designacao.
- **Identificacao do Solo Boss**: evento da agenda cujo nome, normalizado (minusculas, sem
  espacos/hifens/underscores), e `soloboss`. Nada de config nova.
- **"Loot: X" so no aviso de ANTECEDENCIA.** O evento tem `avisar_no_horario = false`; o
  aviso AGORA nao existe para ele e nao deve ganhar a linha nem se existisse.
- **Duas instancias**: o registro do loot consumado usa marcador atomico
  `O_CREAT | O_EXCL`, o mesmo padrao do `RegistroEmDisco` — exatamente uma instancia
  registra, as duas param de anunciar.
- **Comandos dinamicos nao colidem com o vocabulario fixo** (`.cancelar`, `.status`,
  `.solo`, `.party`, `.pt`, `.grupo`, `.voltar`, `.scanner`, `.soloplay`, `.silencio`,
  `.cancelarsilencio`) **nem com `.offline`**, que e convencao humana do grupo e jamais
  pode virar consulta de nick.
- **`.<nick>` so responde nick conhecido**: que ja apareceu no registro de loot OU ja foi
  alvo de um `.loot-<nick>`. Sem isso o scanner responderia lixo a qualquer `.palavra`.
- **Estilo do projeto**: codigo e comentarios em portugues sem acentos, docstrings que
  explicam o PORQUE, funcoes puras com tempo/dados por parametro, testes sem rede.
</decisoes_ja_tomadas>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

@l2scanner/comandos.py
@l2scanner/agenda.py
@l2scanner/sessao.py
@l2scanner/__main__.py
@config.toml
@tests/test_comandos.py
@tests/test_sessao.py
</context>

<convencoes>
- Codigo, comentarios, docstrings, nomes de teste e textos ao usuario em **portugues SEM
  ACENTOS no codigo**. Comentario explica o **PORQUE**, citando a falha que evitaria.
- **Trabalhar SOMENTE dentro do worktree**
  `C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss`.
- Rodar testes com `python -m pytest` (o `.venv` NAO tem pytest; `uv` NAO esta no PATH).
- O tempo entra por parametro em TUDO — `loot.py` segue a mesma disciplina de `agenda.py`:
  nenhum `datetime.now()`, nenhum relogio proprio. Disco so via `tmp_path` nos testes.
- Zero dependencia nova: stdlib apenas.
</convencoes>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: l2scanner/loot.py — o dominio inteiro do loot, puro e testado</name>
  <files>l2scanner/loot.py, tests/test_loot.py</files>
  <read_first>
    - `l2scanner/agenda.py:233-341` (`RegistroEmDisco` — o padrao O_CREAT|O_EXCL a copiar,
      e `podar()` em :315, que e O MOTIVO de o loot ter pasta propria: a poda apaga
      marcador com prefixo de data apos 3 dias, e estatistica de loot nao pode ser podada)
    - `l2scanner/agenda.py:98-120,185-222,358-365` (`Aviso`, `proxima_ocorrencia`,
      `texto_do_aviso`, `chave_da_ocorrencia` — o idioma de slug `re.sub` a reaproveitar)
    - `tests/test_agenda.py` (estilo: classes Test*, docstring com o porque, tmp_path)
  </read_first>

  <behavior>
    Escreva `tests/test_loot.py` PRIMEIRO. Casos, na ordem do risco:

    - **Registro atomico**: `registrar("J4guar", alvo)` duas vezes sobre a mesma pasta ->
      primeira True, segunda False; existe exatamente um arquivo `pegou_*`.
    - **Corrida de duas instancias**: dois `RegistroDeLoot` sobre a MESMA pasta (as duas
      instancias do usuario); ambos com a mesma designacao vencida chamam `consumir` ->
      exatamente um devolve a `Designacao`, o outro devolve None, ha UM `pegou_*`, e
      `proximo.json` sumiu nas duas visoes.
    - **Consumo respeita o horario**: `consumir(agora)` ANTES do alvo nao registra nada e
      mantem `proximo.json`; no alvo em diante, registra e apaga.
    - **Consumo atrasado**: designacao para as 10:00, `consumir` so as 13:07 (as duas
      instancias ficaram desligadas) -> registra com o horario do BOSS (10:00), nao o de
      agora.
    - **`resumo` conta e acha o ultimo**: tres registros de `j4guar` em dias/horas
      diferentes + um de `kaus` -> `resumo("J4GUAR")` da (3, o mais recente) — a
      comparacao e case-insensitive via slug.
    - **`nicks_conhecidos`**: vazio no comeco; apos `designar`, contem o slug; apos so um
      `registrar` direto, tambem. E a uniao dos marcadores `nick_*`, dos `pegou_*` e da
      designacao corrente.
    - **`designacao()` com `proximo.json` corrompido** (lixo, JSON pela metade) -> None,
      sem levantar. Um arquivo meio-escrito nao pode derrubar o laco.
    - **`designar` substitui**: designar `j4guar` e depois `kaus` para o mesmo alvo ->
      `designacao()` devolve kaus. A ultima palavra vence.
    - **`nick_para_o_aviso`**: devolve "J4guar" apenas quando o aviso e ANTES, o evento
      normaliza para `soloboss` e `designacao.alvo == aviso.alvo`. Quatro negativos:
      tipo AGORA, evento "TvT", alvo de outra ocorrencia (12:00 vs 10:00), designacao
      None.
    - **`eh_solo_boss`**: "Solo Boss", "solo boss", "SoloBoss", "SOLO-BOSS" -> True;
      "TvT", "Prime", "Solo" -> False.
    - **`responder_consulta`**: com 7 registros e ultimo hoje as 10:00 ->
      "J4guar pegou 7 loots de Solo Boss. Ultimo: hoje as 10:00."; com 1 -> "1 loot"
      (singular); com 0 -> "J4guar ainda nao pegou nenhum loot de Solo Boss."; se o nick
      consultado e o designado corrente, a resposta termina com "O proximo e dele.".
    - **`responder_designacao`**: com agenda contendo o Solo Boss, `.loot-j4guar` as
      09:05 -> "J4guar pega o loot do proximo Solo Boss, as 10:00." e a designacao fica
      gravada com alvo 10:00; substituindo designacao de outro nick para o MESMO alvo, a
      resposta acrescenta "(Era do Kaus.)"; agenda SEM Solo Boss -> mensagem de erro
      clara, nada gravado.
    - **`descrever_momento`**: mesmo dia -> "hoje as 10:00"; vespera -> "ontem as 22:00";
      mais antigo -> "em 23/08 as 14:00".
  </behavior>

  <action>
Criar `l2scanner/loot.py`, stdlib apenas (`os`, `re`, `json`, `dataclasses`, `datetime`,
`pathlib`) + `l2scanner.agenda` (`Aviso`, `TipoDeAviso`, `EventoAgendado`,
`proxima_ocorrencia`). **NUNCA importar `l2scanner.comandos` nem `l2scanner.sessao`** —
`comandos.py` e `sessao.py` e que vao importar daqui, e um ciclo mataria os dois.

**Normalizacao**
- `apelido(nick) -> str`: `re.sub(r"[^a-z0-9]+", "-", nick.lower()).strip("-")` — o mesmo
  idioma de slug de `agenda.chave_da_ocorrencia`.
- `exibir(nick) -> str`: primeira letra maiuscula (`nick[:1].upper() + nick[1:]`). E o que
  transforma o `.loot-j4guar` digitado em "J4guar" na resposta — o comando chega minusculo
  e a resposta nao pode parecer descuidada.
- `eh_solo_boss(nome) -> bool`: minusculas e remocao de espacos/hifens/underscores ==
  `"soloboss"`. Comparacao tolerante por decisao do usuario; sem config nova.

**`@dataclass(frozen=True) Designacao`**: `nick: str` (como digitado), `alvo: datetime`
(a ocorrencia do boss que ela mira), `designado_em: datetime`.

**`class RegistroDeLoot(pasta: Path)`** — cria a pasta, NAO tem poda. Tres tipos de
arquivo convivem nela, cada um com prefixo proprio (mesma tecnica dos namespaces do
`.agenda/`):

- `pegou_{YYYY-MM-DD}-{HHMM}_{slug}` — um loot consumado (arquivo vazio; a identidade e o
  nome). Ex.: `pegou_2026-08-25-1000_j4guar`.
- `nick_{slug}` — este nick ja foi alvo de `.loot-<nick>` alguma vez. E o que alimenta o
  portao do `.<nick>`.
- `proximo.json` — a designacao corrente: `{"nick": "J4guar", "alvo": "...iso...",
  "designado_em": "...iso..."}`.

Metodos:
- `_criar(nome) -> str` interno, tri-estado `"criado" | "ja_existia" | "falhou"`, com
  `os.open(O_CREAT | O_EXCL | O_WRONLY)`. Tri-estado porque `consumir` precisa distinguir
  "a outra instancia registrou" (apaga a designacao) de "disco falhou" (MANTEM a
  designacao para tentar de novo no proximo tick). O `marcar` do RegistroEmDisco colapsa
  falha em True porque aviso perdido e pior que duplicado; aqui e o contrario — registro
  perdido em silencio e estatistica errada para sempre.
- `registrar(nick, alvo: datetime) -> bool`: True somente quando `_criar` do `pegou_*`
  devolveu "criado".
- `registros() -> list[tuple[str, datetime]]`: parseia os `pegou_*`; nome malformado e
  pulado sem levantar.
- `resumo(nick) -> tuple[int, datetime | None]`: total e o mais recente para
  `apelido(nick)`.
- `designar(nick, alvo, agora) -> Designacao`: grava `proximo.json` ATOMICAMENTE —
  escreve `proximo.json.tmp-{os.getpid()}` e `os.replace` por cima (atomico no Windows no
  mesmo volume; o pid no nome impede uma instancia de atropelar o tmp da outra). Tambem
  toca `nick_{slug}` (idempotente, `_criar` ignorando "ja_existia"). Duas designacoes
  simultaneas: a ultima vence, e esta certo.
- `designacao() -> Designacao | None`: le `proximo.json`; ausente, ilegivel ou com campos
  invalidos -> None, sem levantar.
- `consumir(agora) -> Designacao | None`: sem designacao ou `agora < alvo` -> None. Senao
  `_criar` do `pegou_*`: "criado" -> apaga `proximo.json` (`unlink(missing_ok=True)`) e
  devolve a Designacao (ESTE processo registrou — e ele que loga); "ja_existia" -> apaga
  o json e devolve None (a outra instancia venceu); "falhou" -> NAO apaga e devolve None
  (proximo tick tenta de novo).
- `nicks_conhecidos() -> frozenset[str]`: slugs da uniao `nick_*` + `pegou_*` +
  designacao corrente.

**Funcoes puras de texto e decisao** (tempo por parametro, sem disco alem do registro
recebido):
- `descrever_momento(alvo, agora) -> str`: "hoje as HH:MM" / "ontem as HH:MM" /
  "em DD/MM as HH:MM".
- `nick_para_o_aviso(aviso: Aviso, designacao: Designacao | None) -> str | None`:
  `exibir(designacao.nick)` apenas quando `aviso.tipo is TipoDeAviso.ANTES`,
  `eh_solo_boss(aviso.evento)` e `designacao.alvo == aviso.alvo`. A comparacao de alvo e
  o que impede a designacao das 10:00 de vazar para o aviso do boss das 12:00 quando
  ninguem consumiu a tempo.
- `responder_consulta(registro, nick, agora) -> str`: usa `resumo` + `descrever_momento`
  + designacao corrente. Formatos exatos no <behavior>.
- `responder_designacao(registro, eventos, agora, nick) -> str`: acha o evento com
  `eh_solo_boss`; sem ele (ou sem proxima ocorrencia), devolve "Nao achei o Solo Boss na
  agenda do config.toml — nao da para marcar o loot." sem gravar nada. Com ele,
  `proxima_ocorrencia(agora, [evento_solo])` da o alvo, `registro.designar(...)` grava, e
  a resposta confirma nick e horario — mencionando o substituido quando havia designacao
  de OUTRO nick para o MESMO alvo.
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -m pytest tests/test_loot.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -c "import ast; a=ast.parse(open('l2scanner/loot.py',encoding='utf-8').read()); m={(n.module or '') if isinstance(n,ast.ImportFrom) else n.names[0].name for n in ast.walk(a) if isinstance(n,(ast.Import,ast.ImportFrom))}; proibidos=[x for x in m if 'comandos' in x or 'sessao' in x or 'urllib' in x]; assert not proibidos, proibidos; print('imports ok:', sorted(m))"</automated>
  </verify>

  <done>
`tests/test_loot.py` passa, incluindo a corrida de duas instancias (um registra, o outro
cala, um unico `pegou_*`) e o consumo atrasado com o horario do boss. `loot.py` nao
importa `comandos` nem `sessao` e nao fala rede.
  </done>

  <reversibility rating="reversible">
    Modulo novo e isolado ate a Task 2; apagar o arquivo devolve o comportamento anterior.
  </reversibility>
</task>

<task type="auto" tdd="true">
  <name>Task 2: os comandos `.loot-nick` e `.nick` — interpretar, portar e obedecer</name>

  <precondition>Task 1 concluida: `l2scanner/loot.py` existe e `tests/test_loot.py` passa.</precondition>
  <files>l2scanner/comandos.py, l2scanner/__main__.py, tests/test_comandos.py</files>
  <read_first>
    - `l2scanner/comandos.py:151-177` (`interpretar` — repare que ele REMOVE hifens do
      miolo; e por isso que `.loot-j4guar` passa ileso por ele e o dinamico precisa olhar
      a palavra CRUA)
    - `l2scanner/comandos.py:180-234` (`comandos_novos` e as travas; `MensagemDeComando`)
    - `l2scanner/__main__.py:427-539` (`atender_comandos` e os `_obedecer_*` — o molde do
      dispatch e do "responde onde perguntaram")
    - `tests/test_comandos.py:22-29,63-75` (helper `msg` e o teste do vocabulario fechado,
      que VAI precisar crescer — a docstring dele ja diz "quando ela crescer, e para
      crescer de proposito")
  </read_first>

  <behavior>
    Testes novos em `tests/test_comandos.py` (escrever antes da implementacao):

    - `.loot-j4guar` -> `(Comando.LOOT_DESIGNAR, "j4guar")`; `.LOOT-J4guar` preserva o
      nick como digitado ("J4guar"); `.loot j4guar` (duas palavras) tambem designa;
      `.loot-` sozinho e `.loot` sozinho -> None.
    - `.j4guar` com "j4guar" em `nicks_conhecidos` -> `(Comando.LOOT_CONSULTA, "j4guar")`;
      SEM estar no conjunto -> None (o scanner nao responde lixo).
    - `.offline` -> None SEMPRE, mesmo com "offline" no conjunto de nicks. Convencao
      humana do grupo, nunca comando.
    - Palavra do vocabulario fixo nunca vira consulta: `.status` com "status" nos nicks
      conhecidos continua `Comando.STATUS` sem argumento.
    - `comandos_novos` com `nicks_conhecidos` produz os dois comandos novos com
      `argumento` preenchido, e todas as travas existentes (incoming, private, dedupe,
      telefone) continuam valendo para eles — pelo menos um caso: `.loot-j4guar` de
      telefone NAO autorizado e descartado.
    - Atualizar `test_o_vocabulario_e_fechado` para o novo conjunto, mantendo o espirito:
      a lista cresceu de proposito, e o teste continua sendo o alarme de crescimento
      acidental.
  </behavior>

  <action>
**`l2scanner/comandos.py`**

- `Comando` ganha `LOOT_DESIGNAR = "loot_designar"` e `LOOT_CONSULTA = "loot_consulta"`.
- `MensagemDeComando` ganha `argumento: str | None = None` (o nick, como digitado).
- Nova funcao pura `interpretar_dinamico(texto, nicks_conhecidos) ->
  tuple[Comando, str] | None`, ao lado de `interpretar`, olhando a PRIMEIRA PALAVRA CRUA
  (com hifens — nao reutilizar o miolo sem hifen de `interpretar`):
  - exige o `PREFIXO`;
  - `.loot-<nick>` ou `.loot <nick>` (segunda palavra): nick valido =
    `re.fullmatch(r"[A-Za-z0-9]{2,16}", nick)` -> `(LOOT_DESIGNAR, nick)`. O charset e o
    de nick de L2; o minimo de 2 evita que `.loot-a` de um dedo escorregado vire
    designacao.
  - senao, palavra unica `.{nick}` com nick valido, cujo `apelido(nick)` esta em
    `nicks_conhecidos`, cujo lowercase NAO esta em `_VOCABULARIO` e NAO e `"offline"` ->
    `(LOOT_CONSULTA, nick)`. O portao por nick conhecido e decisao do usuario: sem ele o
    scanner responderia a qualquer `.palavra` do grupo.
- `comandos_novos(mensagens, ja_obedecidos, telefones=None,
  nicks_conhecidos=frozenset())`: onde hoje descarta quando `interpretar` devolve None,
  tentar `interpretar_dinamico` antes de descartar. O vocabulario FIXO vem primeiro —
  precedencia explicita, para um nick homonimo de comando jamais sombrear o comando.
  Preencher `comando` e `argumento` na `MensagemDeComando`.

**`l2scanner/__main__.py`**

- `PASTA_LOOT = RAIZ / ".loot"` ao lado de `PASTA_AGENDA` (linha 80). Pasta propria
  porque o `RegistroEmDisco.podar()` apaga marcadores com prefixo de data em 3 dias, e
  estatistica de loot e para sempre.
- `atender_comandos(..., rastreador=None, loot=None)`: novo parametro keyword. Passar
  `nicks_conhecidos=loot.nicks_conhecidos() if loot else frozenset()` na chamada de
  `comandos_novos`. Dois ramos novos no dispatch, entre STATUS e o `else`:
  - `LOOT_DESIGNAR` -> `resposta = responder_designacao(loot, eventos_agendados, agora,
    pedido.argumento)` (import de `l2scanner.loot`); `avisar_o_grupo = False` — o grupo
    vai ficar sabendo pelo proprio aviso de antecedencia com "Loot: X"; ecoar agora seria
    dizer a mesma coisa duas vezes, e o grupo nem entrega incoming (os comandos chegam
    pelo privado).
  - `LOOT_CONSULTA` -> `resposta = responder_consulta(loot, pedido.argumento, agora)`;
    `avisar_o_grupo = False` — pergunta pessoal, mesmo racional do `.status`.
  - Nos dois ramos, `loot is None` -> resposta "Nao consigo mexer no loot agora." (mesmo
    padrao do `_obedecer_modo` sem rastreador).
- Nos DOIS lacos, construir `registro_de_loot = RegistroDeLoot(PASTA_LOOT)` junto do
  `RegistroEmDisco` e passar `loot=registro_de_loot` nas chamadas de `atender_comandos`
  (`laco_da_agenda` linha ~668 e `laco_principal` linha ~939 — na do laco principal,
  manter `rastreador` posicional como esta e acrescentar `loot=` por keyword).
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -m pytest tests/test_comandos.py tests/test_loot.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -c "import ast,sys; sys.path.insert(0,'.'); from l2scanner.comandos import interpretar, interpretar_dinamico, Comando; assert interpretar('.status') is Comando.STATUS; assert interpretar_dinamico('.offline', frozenset({'offline'})) is None; assert interpretar_dinamico('.loot-J4guar', frozenset())==(Comando.LOOT_DESIGNAR,'J4guar'); print('portoes ok')"</automated>
  </verify>

  <done>
`.loot-j4guar` e `.j4guar` (nick conhecido) atravessam `comandos_novos` com todas as
travas antigas valendo; `.offline` e `.palavra` desconhecida continuam mudos; o
vocabulario fixo tem precedencia. `atender_comandos` responde os dois na conversa de
origem, sem eco no grupo. Suite de comandos verde.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: "Loot: X" no aviso de antecedencia e o consumo automatico nos dois lacos</name>

  <precondition>Tasks 1 e 2 concluidas: loot.py e o dispatch de comandos passam nos testes.</precondition>
  <files>l2scanner/agenda.py, l2scanner/sessao.py, l2scanner/__main__.py, tests/test_agenda.py, tests/test_sessao.py</files>
  <read_first>
    - `l2scanner/sessao.py:186-205` (`_processar_agenda` — o unico lugar do laco principal
      onde `texto_do_aviso` e chamado) e `:50-71` (`ResultadoDoTick` — o porque de
      resultado estruturado)
    - `l2scanner/__main__.py:680-689` (o loop de avisos do `laco_da_agenda` — o SEGUNDO
      lugar; esquecer ele deixaria o modo --so-agenda sem a linha de loot)
    - `tests/test_sessao.py:27-75` (`SilencioFalso`, `nova_sessao`, `em()` — reaproveitar,
      nao inventar fixture nova)
  </read_first>

  <behavior>
    Em `tests/test_agenda.py`:
    - `texto_do_aviso(aviso_antes, loot="J4guar")` termina com "Loot: J4guar." e o texto
      SEM o parametro e byte a byte o de hoje (regressao: chamadas existentes nao mudam).
    - `texto_do_aviso(aviso_agora, loot="J4guar")` NAO ganha a linha — so a antecedencia
      carrega o loot, por decisao do usuario.

    Em `tests/test_sessao.py` (usar `nova_sessao` com um `RegistroDeLoot(tmp_path /
    "loot")` novo parametro, evento `EventoAgendado("Solo Boss", horarios=((10, 0),),
    avisar_no_horario=False)` como no config real, e `em()` para o tempo):
    - **O aviso sai com o nome**: designacao para o boss das 10:00; tick as 09:50 ->
      `resultado.avisos` contem um texto com "Solo Boss" e "Loot: J4guar".
    - **Sem designacao, sem linha**: mesmo cenario sem designar -> o aviso sai SEM
      "Loot".
    - **TvT nunca ganha a linha**: agenda com TvT + designacao de Solo Boss ativa -> o
      aviso do TvT sai sem "Loot".
    - **Consumo no horario**: designacao para 10:00; tick as 10:00 ->
      `resultado.loot_consumado` e a Designacao, ha um `pegou_*` na pasta e
      `proximo.json` sumiu; tick seguinte -> `loot_consumado` None (nao registra em
      dobro).
    - **Duas instancias**: duas `Sessao` sobre a MESMA pasta de loot, ambas tick as 10:00
      -> exatamente uma tem `loot_consumado`, um unico `pegou_*`.
    - **O boss seguinte nao herda**: apos o consumo das 10:00, tick as 11:50 (aviso do
      boss das 12:00) -> aviso sem "Loot" (a designacao foi consumida, requisito 4).
  </behavior>

  <action>
**`l2scanner/agenda.py`** — `texto_do_aviso(aviso, loot: str | None = None)`: quando
`loot` vem preenchido E `aviso.tipo is TipoDeAviso.ANTES`, acrescentar ` Loot: {loot}.`
ao fim do texto atual. Assinatura retrocompativel: todo call site existente continua
valido sem mudanca. `agenda.py` NAO importa `loot.py` — quem decide SE ha loot e o
chamador; a agenda so formata. (E o que mantem `agenda.py` sem conhecer designacao
nenhuma, na mesma linha de `console.py` nao ganhar relogio.)

**`l2scanner/sessao.py`**
- `Sessao.__init__(..., loot=None)` — default None mantem os testes e chamadas atuais
  intactos.
- `ResultadoDoTick` ganha `loot_consumado: "Designacao | None" = None` (import de
  `l2scanner.loot`; loot.py nao importa sessao, entao nao ha ciclo). Estruturado, nao
  texto — pelo mesmo motivo de `despachos` existir: teste afirma estrutura, nao redacao.
- `_processar_agenda`: antes do loop de avisos, `designacao = self.loot.designacao() if
  self.loot else None`. No loop, `texto = texto_do_aviso(aviso,
  nick_para_o_aviso(aviso, designacao))`. DEPOIS do loop, `if self.loot:
  resultado.loot_consumado = self.loot.consumir(agora)`. A ordem (avisos antes, consumo
  depois) e indiferente no relogio — o aviso ANTES vence 10 min antes do alvo e o consumo
  so dispara no alvo — mas fixa-la torna o tick deterministico para o teste.

**`l2scanner/__main__.py`**
- `laco_da_agenda`: antes do `for aviso in avisos_devidos(...)`, ler `designacao =
  registro_de_loot.designacao()`; dentro, `texto = texto_do_aviso(aviso,
  nick_para_o_aviso(aviso, designacao))`. Depois do loop, `consumida =
  registro_de_loot.consumir(agora)`; se veio, `log.info(destacar(f"Loot do Solo Boss das
  {consumida.alvo.strftime('%H:%M')} registrado para {exibir(consumida.nick)}"))`. So
  log, sem WhatsApp: o Solo Boss ja e 12 ocorrencias/dia e a disciplina de volume da
  agenda (decisao [agenda] do STATE.md) vale aqui tambem.
- `laco_principal`: passar `loot=registro_de_loot` na construcao da `Sessao` (linha ~889)
  e, no pos-tick onde `resultado.avisos` e logado, logar tambem `resultado.loot_consumado`
  quando presente, com o mesmo texto acima.
  </action>

  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -m pytest tests/test_agenda.py tests/test_sessao.py tests/test_loot.py tests/test_comandos.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && python -m pytest -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings/.claude/worktrees/loot-solo-boss" && TOCADOS=$(git diff --name-only -- l2scanner/rastreador.py l2scanner/visao.py l2scanner/captura_janela.py l2scanner/notificador.py l2scanner/cliente.py l2scanner/console.py l2scanner/relogio.py); if [ -n "$TOCADOS" ]; then echo "ARQUIVO PROIBIDO ALTERADO: $TOCADOS"; exit 1; fi; echo "deteccao e transporte intactos"</automated>
  </verify>

  <done>
Suite inteira verde. O aviso de antecedencia do Solo Boss designado carrega "Loot: X" nos
DOIS lacos; o consumo registra uma unica vez com duas instancias e a designacao nao vaza
para o boss seguinte. Nenhum arquivo do caminho de deteccao ou de transporte aparece no
diff.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WhatsApp/Chatwoot -> scanner | Texto de qualquer pessoa nas conversas de comando passa a poder virar consulta (`.nick`) e mutacao de estado (`.loot-nick`). |
| disco compartilhado (`.loot/`) | Duas instancias leem e escrevem a mesma pasta; um arquivo meio-escrito nao pode derrubar nenhuma das duas. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-cou-01 | Spoofing | `.loot-<nick>` / `.<nick>` | medium | mitigate | As travas existentes de `comandos_novos` valem integralmente para os comandos novos: so `incoming`, nao-`private`, dedupe por id, e allowlist de telefone (`autor_autorizado`). Testado na Task 2 com um `.loot-` de telefone nao autorizado sendo descartado. |
| T-cou-02 | Elevation of Privilege | `interpretar_dinamico` | medium | mitigate | Superficie dinamica CONTIDA: nick restrito a `[A-Za-z0-9]{2,16}`, consulta so de nick conhecido, vocabulario fixo com precedencia e `.offline` excluido por nome. Um `.palavra` arbitrario continua morrendo em silencio. |
| T-cou-03 | Tampering | `proximo.json` / `pegou_*` | low | accept | Arquivos locais no PC do proprio usuario, mesmo perfil de confianca do `.agenda/` e do `calibration.json` ja existentes. Leitura defensiva (JSON corrompido -> None) cobre corrupcao acidental, que e o caso real. |
| T-cou-04 | Denial of Service | consumo com disco falhando | low | mitigate | `_criar` tri-estado: falha de disco mantem a designacao e tenta no proximo tick, em vez de consumir em silencio ou levantar dentro do laco. |
| T-cou-SC | Tampering | npm/pip/cargo installs | high | mitigate | **Nenhum pacote instalado.** `loot.py` e stdlib pura; o gate de imports da Task 1 falha o plano se algo de fora entrar. |
</threat_model>

<verification>
1. `python -m pytest -q` no worktree — suite inteira verde (os 446+ de hoje + os novos).
2. Simulacao sem jogo e sem rede: `python -m pytest tests/test_sessao.py -q -k loot`
   cobre o fio designar -> aviso com "Loot:" -> consumo -> boss seguinte limpo.
3. `git diff --stat` — producao tocada somente em `loot.py` (novo), `comandos.py`,
   `agenda.py`, `sessao.py` e `__main__.py`.
4. Em campo (fora do plano, primeira sessao real): mandar `.loot-j4guar` no privado,
   conferir a resposta, esperar o aviso de antecedencia com "Loot: J4guar" no grupo e,
   depois do horario do boss, mandar `.j4guar` e ver a contagem crescida.
</verification>

<success_criteria>
- Os quatro requisitos do pedido cobertos por teste: registro duravel, consulta `.nick`,
  designacao `.loot-nick` refletida no aviso de antecedencia, e consumo automatico com o
  horario do boss.
- Duas instancias sobre a mesma pasta registram UM loot e a designacao some — provado por
  teste de corrida, nao por inspecao.
- `.offline`, `.palavra` desconhecida e o vocabulario fixo intactos; zero mensagem nova
  nao solicitada no grupo (a unica mudanca visivel no grupo e a linha "Loot: X" no aviso
  que ja existia).
- Zero dependencia nova; `.loot/` separado do `.agenda/` para a poda de 3 dias nunca
  comer estatistica.
</success_criteria>

<output>
Create `.planning/quick/260825-cou-controle-de-loot-do-solo-boss-via-comand/260825-cou-SUMMARY.md` when done
</output>
