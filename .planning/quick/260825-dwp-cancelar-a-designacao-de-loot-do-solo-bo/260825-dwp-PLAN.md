---
phase: quick-260825-dwp
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
  - tests/test_sessao.py
autonomous: true
requirements: [QUICK-260825-dwp]

estimate:
  tokens: 55000
  raw_tokens: 28000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "`.loot-` (nada depois do hifen) APAGA a designacao corrente, e o aviso de antecedencia do proximo Solo Boss volta a sair SEM o trecho 'Loot:' (D-01)."
    - "`.loot` SOZINHO continua morrendo em silencio — nunca cancela, nunca designa (D-02). Comando sem argumento nao pode ser destrutivo."
    - "`.loot-cancelar`, `.loot-ninguem`, `.loot-nenhum` e `.loot-limpar` cancelam igual ao `.loot-` (D-03), e o preco (um personagem chamado 'Cancelar' nao pode ser designado) esta escrito no codigo."
    - "Cancelar sem ter designacao nenhuma NAO levanta e responde com honestidade — e cancelar duas vezes seguidas (as duas instancias do usuario) tambem nao levanta (D-05)."
    - "A resposta diz de QUEM era e de QUAL boss: 'Loot do Solo Boss das 10:00 cancelado — era do TioMad. O aviso sai sem nome.' (D-06)"
    - "A TROCA continua funcionando: `.loot-kaus` por cima de `.loot-j4guar` no mesmo boss segue anunciando '(Era do J4guar.)' — regressao."
    - "Um nick normal continua designando: `.loot-J4guar` nao virou cancelamento por acidente."
    - "As quatro travas de seguranca continuam valendo de graca: so `incoming`, nao `private`, dedupe por id e allowlist de telefone — porque o comando novo passa pelo mesmo `comandos_novos` (D-04)."
    - "O historico nao e tocado: cancelar apaga a VEZ, nunca os `pegou_*` nem os `nick_*`. O `.<nick>` continua contando os mesmos loots depois de um cancelamento."
    - "A suite inteira segue verde (446+ testes), sem o jogo aberto e sem rede."
  artifacts:
    - "l2scanner/loot.py — RegistroDeLoot.cancelar() e responder_cancelamento()"
    - "l2scanner/comandos.py — Comando.LOOT_CANCELAR, _PALAVRAS_DE_CANCELAMENTO, ramo de cancelamento em interpretar_dinamico"
    - "l2scanner/__main__.py — ramo Comando.LOOT_CANCELAR em atender_comandos, com avisar_o_grupo=False"
    - "tests/test_loot.py — cancelamento no registro e no texto"
    - "tests/test_comandos.py — as sintaxes que cancelam, as que nao cancelam, e o cancelamento na costura"
    - "tests/test_sessao.py — a prova de fim a fim: designar, cancelar, e o aviso sai sem 'Loot:'"
  key_links:
    - "interpretar_dinamico -> Comando.LOOT_CANCELAR: o ramo de cancelamento tem que vir ANTES do _NICK_VALIDO, senao `.loot-cancelar` designa um personagem chamado 'Cancelar'."
    - "RegistroDeLoot.cancelar() -> proximo.json: unlink(missing_ok=True) e o que torna o cancelamento idempotente entre as duas instancias."
    - "cancelar() -> nick_para_o_aviso(): sem `proximo.json`, `designacao()` devolve None e o aviso perde a linha do loot — o caminho ja existe, o cancelamento so precisa alimenta-lo."
    - "atender_comandos -> responder_cancelamento: o dispatch e o unico ponto onde o comando vira acao; sem ele o parser reconhece e nada acontece."
---

<objective>
Dar ao `.loot-` o poder de APAGAR a designacao de loot do Solo Boss.

Hoje da para designar (`.loot-j4guar`) e da para trocar (a ultima palavra vence,
com "(Era do TioMad.)"), mas nao ha como deixar o proximo boss SEM NINGUEM. O
`.loot-` — exatamente a sintaxe que o usuario quer para cancelar — cai no
`_NICK_VALIDO.fullmatch("")`, falha e morre em silencio.

Purpose: quando a party desmarca o revezamento (o designado saiu, o boss virou
free-for-all), o registro tem que poder voltar ao estado "sem dono" sem editar
arquivo e sem reiniciar o scanner.

Output: `Comando.LOOT_CANCELAR`, `RegistroDeLoot.cancelar()`,
`responder_cancelamento()`, o dispatch em `atender_comandos`, e os testes que
provam que o aviso de antecedencia volta a sair sem "Loot:".
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

- **D-01** — `.loot-` (nada depois do hifen) CANCELA a designacao corrente.
- **D-02** — `.loot` SOZINHO continua morrendo em silencio. NUNCA cancela.
  Razao: comando sem argumento nao pode ser destrutivo, e quem digita `.loot`
  no meio de um farm provavelmente esta perguntando "quem pega o loot?", nao
  mandando apagar. Um `.loot` que apaga em silencio seria a pior armadilha
  possivel nessa superficie.
- **D-03** — Alem de `.loot-`, valem as palavras reservadas `.loot-cancelar`,
  `.loot-ninguem`, `.loot-nenhum`, `.loot-limpar`. O preco — um personagem
  chamado "Cancelar" nao poderia ser designado — e aceitavel e fica
  DOCUMENTADO no codigo.
- **D-04** — Novo `Comando.LOOT_CANCELAR`, reconhecido dentro de
  `interpretar_dinamico` (que ja trata o prefixo `loot-`). O vocabulario fixo
  mantem precedencia e as quatro travas existentes continuam valendo de graca
  porque o comando passa por `comandos_novos`.
- **D-05** — `RegistroDeLoot.cancelar()` apaga `proximo.json` com
  `unlink(missing_ok=True)` e devolve a `Designacao` anterior (ou None).
  Idempotente entre as duas instancias: cancelar duas vezes nao pode levantar.
- **D-06** — `responder_cancelamento()` diz de QUEM era e de QUAL boss. Sem
  designacao, diz que nao havia nada marcado. Funcao pura, tempo por
  parametro, no estilo de `responder_designacao`.
- **D-07** — Dispatch em `atender_comandos` do `__main__.py` com
  `avisar_o_grupo=False`, pela mesma razao ja documentada no ramo do
  LOOT_DESIGNAR.

**Fora de escopo (ja funciona, so precisa continuar funcionando):** a TROCA.
`designar()` grava por cima e `responder_designacao()` ja anuncia "(Era do
TioMad.)". Nada a construir — so o teste de regressao pedido.

**Discricao do Claude, derivada de D-03:** as palavras reservadas valem tambem
na forma de duas palavras (`.loot cancelar`), porque a alternativa seria
`.loot cancelar` DESIGNAR um personagem inexistente chamado "cancelar" —
exatamente o acidente que D-03 aceita pagar para evitar. Isto nao conflita com
D-02: D-02 fala do `.loot` SOZINHO, sem argumento nenhum.
</decisions_travadas>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: o caminho inteiro do `.loot-`, de ponta a ponta</name>
  <files>tests/test_loot.py, tests/test_comandos.py, tests/test_sessao.py, l2scanner/loot.py, l2scanner/comandos.py, l2scanner/__main__.py</files>
  <read_first>
    - `l2scanner/loot.py` linhas 176-241 (`designar`, `designacao`, `consumir`) e 327-362 (`responder_designacao`) — o estilo que `cancelar` e `responder_cancelamento` tem que espelhar.
    - `l2scanner/comandos.py` linhas 204-251 (`interpretar_dinamico`) — o ramo `loot-` que vai ganhar o cancelamento.
    - `l2scanner/__main__.py` linhas 502-520 — o ramo `LOOT_DESIGNAR` e o comentario que justifica `avisar_o_grupo=False`.
    - `tests/test_sessao.py` linhas 269-330 (`TestLootNoTick`) — a fixture `nova_sessao(..., loot=...)` e o padrao do teste de fim a fim.
    - `tests/test_comandos.py` linhas 609-696 (`TestLootNaCostura`) — o `LeitorFalso` e o `_atender` que a costura reusa.
  </read_first>
  <behavior>
    RED primeiro. Escreva estes testes, veja falhar, so entao implemente.

    Em `tests/test_loot.py`, numa classe nova `TestCancelamento`:
    - cancelar com designacao devolve a `Designacao` anterior e some com o
      `proximo.json`: depois dele, `registro.designacao()` e None.
    - cancelar nao toca no historico: apos designar "J4guar", registrar um
      loot dele e cancelar, `resumo("J4guar")` continua contando aquele loot e
      `nicks_conhecidos()` continua tendo "j4guar" (cancelar e sobre a VEZ,
      nao sobre a estatistica).
    - `responder_cancelamento` com designacao nomeia o dono e o horario do
      boss: a resposta contem "TioMad" e "10:00".

    Em `tests/test_comandos.py`, dentro de `TestInterpretarDinamico`:
    - `.loot-` devolve `(Comando.LOOT_CANCELAR, "")`.
    - `.loot-J4guar` continua devolvendo `(Comando.LOOT_DESIGNAR, "J4guar")` —
      a prova de que o nick normal nao virou cancelamento por acidente.

    Em `tests/test_sessao.py`, dentro de `TestLootNoTick` — E ESTE E O TESTE
    QUE PROVA QUE APAGOU DE VERDADE:
    - designar "J4guar" para o boss das 10:00, chamar `loot.cancelar()`, rodar
      o tick de 09:50 e afirmar que o aviso saiu (o Solo Boss continua sendo
      anunciado) e que "Loot:" NAO aparece nele. Espelhe
      `test_sem_designacao_o_aviso_sai_sem_a_linha`, que ja existe logo abaixo.
  </behavior>
  <action>
    Implemente o caminho fino inteiro — parser, registro, texto e dispatch —
    numa passada so, para que o `.loot-` funcione de ponta a ponta antes de
    qualquer variacao de sintaxe entrar.

    **`l2scanner/loot.py` — `RegistroDeLoot.cancelar()`** (por D-05): metodo
    novo logo depois de `consumir`. Le a designacao corrente, apaga
    `_ARQUIVO_PROXIMO` com `unlink(missing_ok=True)` e devolve o que leu (ou
    None). Docstring explicando o PORQUE de duas coisas: (1) o `missing_ok` e
    o que torna o cancelamento idempotente entre as duas instancias do
    usuario, que dividem a mesma pasta — a segunda a mandar nao pode levantar;
    (2) o metodo NAO mexe nos `pegou_*` nem nos `nick_*`, porque cancelar e
    sobre de quem e a VEZ, e apagar o historico destruiria o registro que o
    `.<nick>` consulta. A exposicao a `OSError` num disco travado e a mesma
    que `consumir` ja tem — consistencia deliberada, nao esquecimento.

    **`l2scanner/loot.py` — `responder_cancelamento(registro, eventos, agora)`**
    (por D-06): funcao pura no fim do arquivo, ao lado de
    `responder_designacao`, mesmo formato de assinatura e tempo por parametro.
    Chama `registro.cancelar()` PRIMEIRO, antes de olhar a agenda — e a
    imagem-espelho da regra do `responder_designacao`: GRAVAR depende da
    agenda ter um alvo, APAGAR nunca pode depender disso, senao um config
    quebrado prenderia uma designacao para sempre. Documente essa assimetria
    na docstring. Depois monta o texto: com designacao anterior, algo como
    `Loot do {nome} das {HH:MM} cancelado — era do {Nick}. O aviso sai sem
    nome.`, usando `exibir()` para o nick e `anterior.alvo` para a hora; sem
    designacao anterior, diz que nao havia nada marcado para o proximo boss.
    O nome do evento sai do `eventos` pelo mesmo `eh_solo_boss` que
    `responder_designacao` usa (para respeitar a grafia do config.toml), com
    "Solo Boss" como recurso quando a agenda nao tem o evento. Use `agora`
    com `proxima_ocorrencia` para nomear o horario do proximo boss no ramo
    "nao havia nada marcado" — e o que faz o parametro de tempo ganhar o
    lugar dele em vez de existir por simetria.

    **`l2scanner/comandos.py` — `Comando.LOOT_CANCELAR = "loot_cancelar"`**
    (por D-04): novo membro do enum, junto dos outros dois de loot, com
    comentario dizendo que ele e o unico comando DESTRUTIVO da superficie
    dinamica e que por isso a sintaxe dele e explicita.

    **`l2scanner/comandos.py` — o ramo de cancelamento em
    `interpretar_dinamico`** (por D-01/D-03): constante nova ao lado de
    `_PALAVRA_HUMANA`, um frozenset com as quatro palavras reservadas de D-03,
    e um comentario registrando o preco aceito: um personagem chamado
    "Cancelar" nao pode ser designado, e isso e barato perto de nao ter como
    desmarcar. Dentro do ramo `crua.lower().startswith("loot-")`, teste
    argumento vazio ou palavra reservada ANTES do `_NICK_VALIDO` e devolva
    `(Comando.LOOT_CANCELAR, "")`; a ordem e a coisa mais importante do ramo,
    porque "cancelar" casa o charset de nick e viraria designacao. Deixe o
    `_NICK_VALIDO` seguindo depois, intacto.

    **`l2scanner/__main__.py` — o dispatch** (por D-07): importe
    `responder_cancelamento` no bloco `from .loot import (...)` da linha 58 e
    acrescente o ramo `elif pedido.comando is Comando.LOOT_CANCELAR:` logo
    depois do `LOOT_DESIGNAR`, com o mesmo `if loot is None` respondendo que
    nao da para mexer no loot agora, e `avisar_o_grupo = False` com o
    comentario apontando o mesmo racional ja escrito no ramo do designar (os
    comandos chegam pelo privado e o grupo fica sabendo pelo proprio aviso).

    Codigo, comentarios e docstrings em portugues sem acento, no estilo do
    arquivo: a docstring explica o PORQUE, nao o QUE.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_loot.py tests/test_sessao.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -c "import sys; sys.path.insert(0,'.'); from l2scanner.comandos import interpretar_dinamico, Comando; assert interpretar_dinamico('.loot-', frozenset()) == (Comando.LOOT_CANCELAR, ''); assert interpretar_dinamico('.loot-J4guar', frozenset()) == (Comando.LOOT_DESIGNAR, 'J4guar'); print('parser ok')"</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -c "import ast; a=ast.parse(open('l2scanner/loot.py',encoding='utf-8').read()); nomes={n.name for n in ast.walk(a) if isinstance(n,ast.FunctionDef)}; falta=[x for x in ('cancelar','responder_cancelamento') if x not in nomes]; assert not falta, falta; mods={(n.module or '') for n in ast.walk(a) if isinstance(n,ast.ImportFrom)}; proibidos=[m for m in mods if 'comandos' in m or 'sessao' in m]; assert not proibidos, proibidos; print('loot.py ok, sem ciclo de import')"</automated>
  </verify>
  <done>
    `.loot-` chega pelo WhatsApp, apaga a designacao e e respondido na conversa
    de origem dizendo de quem era e de qual boss; o tick de 09:50 volta a
    anunciar o Solo Boss SEM a linha "Loot:". `.loot-J4guar` continua
    designando. Os testes RED escritos no inicio da tarefa estao verdes.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: as sintaxes que cancelam, as que NAO cancelam, e a regressao da troca</name>
  <files>tests/test_comandos.py, tests/test_loot.py, l2scanner/comandos.py</files>
  <read_first>
    - `tests/test_comandos.py` linha 120-122 — `test_loot_sem_nick_nao_faz_nada` afirma HOJE que `.loot-` e None. Esse teste descreve o comportamento que esta sendo trocado e PRECISA ser reescrito, nao contornado.
    - `tests/test_comandos.py` linhas 169-211 (`TestComandosDinamicosNasTravas`) — como o projeto prova que as travas alcancam um comando novo.
    - `tests/test_loot.py` linhas 384-410 — os testes de troca que ja existem.
  </read_first>
  <behavior>
    RED primeiro, de novo. O tema desta tarefa e a FRONTEIRA: o que apaga e o
    que se recusa a apagar.

    Em `tests/test_comandos.py`, `TestInterpretarDinamico`:
    - as quatro palavras reservadas de D-03 cancelam, em laco: `.loot-cancelar`,
      `.loot-ninguem`, `.loot-nenhum`, `.loot-limpar` — e tambem em maiusculas
      (`.LOOT-CANCELAR`), porque o comando e case-insensitive.
    - `.loot cancelar` (duas palavras) tambem cancela — a discricao derivada de
      D-03, para que ninguem designe um personagem chamado "cancelar".
    - **A TRAVA DE D-02**: `.loot` sozinho devolve None. Nao cancela e nao
      designa. Nomeie o teste dizendo isso em voz alta e escreva na docstring
      o porque (comando sem argumento nao pode ser destrutivo; quem digita
      `.loot` no farm esta perguntando, nao mandando apagar).
    - `.loot-a` continua None (o dedo escorregado de um caractere).

    Em `tests/test_comandos.py`, `TestLootNaCostura`, reusando o `_atender`:
    - `.loot-` na costura apaga de verdade (`loot.designacao()` vira None
      depois) e responde SO na conversa de origem — a lista de destinos e
      `["1"]`, sem eco no grupo (D-07).
    - `.loot-` sem nenhuma designacao previa nao levanta e a resposta sai
      mesmo assim (o comando nao pode morrer calado).
    - `.loot-` com `loot=None` responde que nao da para mexer no loot agora,
      igual aos outros dois comandos de loot.

    Em `tests/test_loot.py`, `TestCancelamento`:
    - cancelar duas vezes seguidas nao levanta, e a segunda devolve None — a
      idempotencia entre as duas instancias do usuario (D-05).
    - `responder_cancelamento` sem designacao nenhuma responde com honestidade
      e nao levanta.
    - **REGRESSAO DA TROCA**: `.loot-kaus` depois de `.loot-j4guar` para o
      mesmo boss continua gravando kaus e continua dizendo "(Era do J4guar.)".
      Se ja houver teste equivalente, aponte-o num comentario em vez de
      duplicar — mas o comportamento tem que estar coberto ao fim da tarefa.
  </behavior>
  <action>
    Reescreva `test_loot_sem_nick_nao_faz_nada` (`tests/test_comandos.py`,
    linha ~120) em DOIS testes com nomes que digam a verdade nova: um afirma
    que `.loot-` cancela, o outro afirma que `.loot` sozinho continua sendo
    nada. Nao deixe a assercao antiga viva com um `pytest.skip` nem comentada
    — ela descreve um comportamento que deixou de existir.

    Estenda o ramo `crua.lower() == "loot"` de `interpretar_dinamico` para
    reconhecer a palavra reservada na segunda posicao (`.loot cancelar`) antes
    do `_NICK_VALIDO`, mantendo o `return None` do `.loot` sozinho exatamente
    onde esta. Comente essa linha de retorno com a razao de D-02, porque ela
    parece um esquecimento para quem le sem contexto e um dia alguem vai
    querer "consertar" isso.

    Nao acrescente sintaxe nenhuma alem das de D-01, D-03 e da forma de duas
    palavras justificada acima. A superficie dinamica e superficie de ataque;
    cada forma nova aceita e uma coisa a mais que o scanner obedece.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_comandos.py tests/test_loot.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -c "import sys; sys.path.insert(0,'.'); from l2scanner.comandos import interpretar_dinamico as f, Comando as C; alvo=(C.LOOT_CANCELAR,''); ruins=[t for t in ('.loot-cancelar','.loot-ninguem','.loot-nenhum','.loot-limpar','.LOOT-CANCELAR','.loot cancelar') if f(t, frozenset())!=alvo]; assert not ruins, ruins; assert f('.loot', frozenset()) is None, 'D-02 violado: .loot sozinho virou acao'; assert f('.loot-a', frozenset()) is None; print('fronteiras ok')"</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
  </verify>
  <done>
    As quatro palavras reservadas cancelam, `.loot` sozinho nao faz nada, o
    nick normal continua designando, a troca continua anunciando o
    substituido, e a suite inteira (446+ testes) esta verde.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WhatsApp/Chatwoot -> `comandos_novos` | Texto de terceiro atravessa aqui e vira acao no scanner |
| `interpretar_dinamico` -> `RegistroDeLoot` | Aqui a acao vira ESCRITA/EXCLUSAO em disco duravel |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-dwp-01 | Tampering | `Comando.LOOT_CANCELAR` — primeiro comando destrutivo da superficie dinamica | medium | mitigate | Passa por `comandos_novos`, herdando as quatro travas (so incoming, nao private, dedupe por id, allowlist de telefone). Nenhum caminho novo de entrada e aberto (D-04). |
| T-dwp-02 | Denial of Service | Apagar a designacao por acidente (dedo escorregado) | medium | mitigate | D-02: `.loot` sozinho nunca cancela; sintaxe destrutiva exige hifen ou palavra explicita. E o dano maximo e uma linha a menos num aviso — `.loot-<nick>` recompoe em 3 segundos. |
| T-dwp-03 | Tampering | Cancelamento apagando estatistica de meses | high | mitigate | `cancelar()` toca SO o `proximo.json`; `pegou_*` e `nick_*` ficam intactos, com teste explicito na Task 1. |
| T-dwp-SC | Tampering | npm/pip/cargo installs | high | mitigate | Nao se aplica: ZERO dependencia nova. Tudo e stdlib + modulos ja existentes do projeto. |
</threat_model>

<verification>
1. `python -m pytest -q` — a suite inteira verde, sem jogo aberto e sem rede.
2. `git diff --stat` — nenhum arquivo de deteccao ou transporte tocado
   (`rastreador.py`, `visao.py`, `captura_janela.py`, `notificador.py`,
   `cliente.py`, `console.py`, `relogio.py`, `agenda.py`, `sessao.py`).
3. `git diff` em `l2scanner/` — nenhuma dependencia nova em `pyproject.toml`.
</verification>

<success_criteria>
- `.loot-` e as quatro palavras reservadas apagam a designacao; `.loot` sozinho
  nao faz nada; `.loot-J4guar` continua designando; a troca continua anunciando
  o substituido.
- Depois de um cancelamento, o aviso de antecedencia do proximo Solo Boss sai
  sem "Loot:" — provado por teste de tick, nao por leitura de codigo.
- Cancelar duas vezes nao levanta; cancelar sem designacao responde com
  honestidade.
- A resposta sai so na conversa de origem, sem eco no grupo.
- Suite inteira verde, zero dependencia nova.
</success_criteria>

<output>
Create `.planning/quick/260825-dwp-cancelar-a-designacao-de-loot-do-solo-bo/260825-dwp-SUMMARY.md` when done
</output>
