---
phase: quick-260825-pik
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/agenda.py
  - l2scanner/loot.py
  - l2scanner/comandos.py
  - l2scanner/__main__.py
  - tests/test_loot.py
  - tests/test_comandos.py
  - README.md
autonomous: true
requirements: [QUICK-260825-pik]

estimate:
  tokens: 90000
  raw_tokens: 45000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`.pegou 18:00 Korzis` registra o loot do Solo Boss das 18:00 no nome do Korzis mesmo quando NAO existia registro nenhum daquele boss — o caso que hoje e impossivel, porque um `pegou_*` so nasce de uma designacao anterior consumida (D-03)."
    - "Sem data, o horario resolve para a ocorrencia mais recente que JA PASSOU, nunca para o futuro: as 02h da manha, `.pegou 18:00 <nick>` fala do boss de ONTEM (D-01)."
    - "A resposta SEMPRE diz o dia de volta, por `descrever_momento` — 'de ontem as 18:00', 'de hoje as 18:00', 'de 23/08 as 18:00'. E a mesma rede de seguranca do `.corrigir`: o DIA e justamente o que falta quando o registro alvo e o de ontem (D-01)."
    - "O horario digitado e ENCAIXADO numa ocorrencia real do Solo Boss e o registro usa o horario da ocorrencia, nunca o digitado (D-02)."
    - "Sem boss por perto do horario digitado, o comando RECUSA e diz quais horarios existem — nunca cria registro orfao, porque registro nunca e podado e nao tem backup (D-02)."
    - "Com registro ja existente naquele horario e dono diferente, o `.pegou` TROCA o dono; sem registro, CRIA. Os dois desfechos tem mensagens distintas, mais 'ja era dele' e 'o disco falhou' (D-03)."
    - "`.pegou <hora> <nick>` e `.pegou-<hora> <nick>` fazem a mesma coisa: a forma de duas palavras nunca e opcional num comando que mexe em estado duravel (D-04)."
    - "`.pegou` sozinho nao faz nada, e nao pode ser lido como consulta de um personagem chamado 'Pegou' — o `return None` explicito do ramo e o que fecha essa porta (D-04)."
    - "A gravacao CRIA o registro novo ANTES de apagar o velho, e atribuir para o MESMO apelido do dono atual e no-op puro que nao apaga nada (D-05)."
    - "Depois de qualquer chamada a `atribuir` — criado, corrigido, mesmo_dono ou falhou — existe no maximo um dono e no minimo o que ja existia para aquele alvo: a estatistica nunca encolhe (D-05)."
    - "Nada aqui levanta no meio do farm: data impossivel, agenda sem Solo Boss, pasta ilegivel e nick malformado viram resposta ou silencio, nunca excecao (D-06)."
    - "`.corrigir` continua existindo e continua alcancando so o registro mais recente. `.pegou` e a forma ENDERECADA; os dois coexistem (D-09)."
    - "A suite inteira segue verde (683+ testes coletados hoje), sem o jogo aberto e sem rede."
  artifacts:
    - "l2scanner/agenda.py — `ocorrencias_do_dia` publicado (era `_ocorrencias`), para o encaixe poder enumerar ocorrencias PASSADAS"
    - "l2scanner/loot.py — `NICK_VALIDO`, `PedidoDePegou`, `interpretar_pegou`, `momento_desejado`, `encaixar_na_agenda`, `horarios_do_solo_boss`, `RegistroDeLoot.atribuir`, `responder_atribuicao`, quinto estado `criado` em `Correcao`"
    - "l2scanner/comandos.py — `Comando.LOOT_ATRIBUIR` e os dois ramos de `.pegou` em `interpretar_dinamico`, com `_NICK_VALIDO` importado de `loot`"
    - "l2scanner/__main__.py — ramo `Comando.LOOT_ATRIBUIR` em `atender_comandos`, com `avisar_o_grupo=False`"
    - "tests/test_loot.py — criacao sem registro previo, troca de dono enderecada, resolucao de ontem, virada da meia-noite, encaixe, recusa com a lista de horarios, os quatro estados de disco"
    - "tests/test_comandos.py — as duas sintaxes que registram, as que nao registram, o nick homonimo, e o `.pegou` na costura"
    - "README.md — a familia inteira de comandos de loot na tabela de comandos, que hoje so lista `.cancelar` e `.status`"
  key_links:
    - "`interpretar_pegou` como PORTAO do parser (D-04): `interpretar_dinamico` so devolve `LOOT_ATRIBUIR` quando ela aceita o argumento. Uma gramatica em comandos.py e outra em loot.py divergiriam no primeiro ajuste — a mesma funcao decide nos dois lugares."
    - "`momento_desejado` -> `encaixar_na_agenda` -> `atribuir(nick, alvo)`: o `alvo` que chega no disco e SEMPRE o da ocorrencia encaixada (D-02). Deixar o horario digitado passar direto criaria `pegou_2026-08-24-1805_korzis`, invisivel para qualquer consulta futura por horario de boss."
    - "`encaixar_na_agenda` devolvendo None -> recusa com a lista de horarios (D-02): e o unico ponto entre 'nao entendi' e um registro orfao permanente."
    - "`atribuir()` -> `_criar` -> `unlink`: a ORDEM e o link critico (D-05), a mesma de `corrigir`. Inverter perde o loot em silencio."
    - "`donos == [slug_novo]` -> retorno antecipado (D-05): sem essa guarda, atribuir ao dono que ja e o dono faz o `_criar` devolver 'ja_existia' e o `unlink` destruir o unico registro que existia."
    - "`atender_comandos` -> `responder_atribuicao`: o dispatch e o unico ponto onde o comando vira acao; sem ele o parser reconhece e nada acontece."
---

<objective>
Dar ao usuario um jeito de dizer, pelo WhatsApp, QUEM pegou o loot de um boss
que ja passou — mesmo quando ninguem tinha marcado nada antes.

O caso real, nas palavras do usuario: *"nao consegui atribuir o loot do boss das
18h e a Korzis pegou"*. Hoje isso e impossivel por construcao. Um `pegou_*` so
vem ao mundo quando havia designacao previa e o `consumir()` a transformou em
registro quando o horario chegou (`loot.py:258`). Sem designacao previa NAO
EXISTE registro nenhum. E o `.corrigir` (`loot.py:287`) so troca o dono do
registro MAIS RECENTE ja consumado — nao alcanca um horario especifico nem o
caso "nao ha registro algum".

Purpose: a estatistica de loot e o unico estado deste projeto que nunca e
podado — "quantos loots a Korzis pegou" e uma pergunta sobre meses. Um boss que
some da contagem porque o scanner estava fora do ar naquela hora e um buraco
permanente, e o unico conserto hoje e criar arquivo a mao no Explorer.

Output: `Comando.LOOT_ATRIBUIR`, a gramatica `.pegou [data] <hora> <nick>`, a
resolucao de horario com encaixe na agenda, `RegistroDeLoot.atribuir()`,
`responder_atribuicao()`, o dispatch, e os testes que provam que o registro
nasce no horario certo do boss certo — ou nao nasce.
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
Decisoes do usuario, coletadas antes deste plano. NAO revisitar, NAO propor
alternativa, NAO simplificar, NAO adiar para "uma proxima versao".

- **D-01 — DATA OPCIONAL.** `.pegou 18:00 Korzis` resolve para a ocorrencia
  mais recente que JA PASSOU. Se sao 02h e o usuario diz 18:00, isso e ONTEM —
  nunca resolve para o futuro. `.pegou 24/08 18:00 Korzis` permite ser
  explicito. A resposta SEMPRE diz o dia de volta para conferencia, via
  `descrever_momento`, exatamente como o `.corrigir` faz: a docstring em
  `loot.py:532` explica que o DIA e justamente a informacao que falta quando o
  registro errado e o de ontem.

- **D-02 — ENCAIXE NA AGENDA.** O horario dado e casado contra uma ocorrencia
  REAL de Solo Boss (via `eh_solo_boss` e a lista de `EventoAgendado` — o mesmo
  caminho que `responder_correcao` usa em `loot.py:544`). O registro usa o
  horario EXATO da ocorrencia encaixada, nunca o digitado. Sem boss por perto,
  RECUSA e diz quais horarios existem — nunca cria registro orfao, porque
  registro e permanente e nunca podado (`loot.py:126`).

- **D-03 — COMPORTAMENTO UNIFICADO.** Se ja existe registro naquele horario com
  dono diferente, o comando TROCA o dono (mesma semantica de uma correcao); se
  nao existe, CRIA. A resposta distingue os casos com mensagens diferentes,
  seguindo o tri-estado ja estabelecido em `loot.py:100` — "ja era dele", "nao
  tinha nada para corrigir" e "o disco falhou" sao mensagens deliberadamente
  distintas, e colapsar qualquer par delas faz o bot mentir sobre o que acabou
  de acontecer com a estatistica.

- **D-04 — GRAMATICA.** Duas formas, hifen e espaco, seguindo a licao
  documentada em `comandos.py:295`: a forma de duas palavras NUNCA e opcional
  num comando que mexe em estado duravel. `.pegou` sozinho nao faz nada, e o
  ramo termina com `return None` EXPLICITO — sem ele o fluxo cai no ramo de
  consulta logo abaixo, onde `_NICK_VALIDO` casa a palavra "pegou" e um
  personagem homonimo transformaria o comando numa consulta. Foi exatamente
  esse erro que fez `.loot cancelar` DESIGNAR um personagem chamado "cancelar".
  Nick continua sendo `[A-Za-z0-9]{2,16}`.

- **D-05 — ESCRITA EM DISCO.** Segue a ordem CRIAR-ANTES-DE-APAGAR de
  `corrigir` (`loot.py:292`) e o tri-estado de `_criar` (criado | ja_existia |
  falhou). A pasta e COMPARTILHADA entre as duas instancias do usuario:
  idempotencia e tolerancia a `FileExistsError` nao sao detalhe.

- **D-06 — NUNCA LEVANTAR NO MEIO DO FARM.** Nome malformado e pulado, nao
  explodido. Vale para data impossivel, agenda sem Solo Boss e pasta ilegivel.

- **D-07 — VOZ.** Codigo, comentarios e textos ao usuario em portugues (pt-BR),
  no estilo do arquivo. Este codebase escreve docstrings longas que justificam
  POR QUE um detalhe nao e detalhe. Escreva assim; comentario magro aqui e
  regressao de estilo.

- **D-08 — TESTES.** Cobertura para: gramatica (incluindo o nick homonimo e a
  forma incompleta), resolucao de data/hora (com enfase na virada da
  meia-noite), encaixe na agenda, recusa quando nao ha boss por perto, e os
  estados de escrita em disco.

- **D-09 — `.pegou` E `.corrigir` COEXISTEM.** O `.corrigir` permanece como o
  atalho "o mais recente" e o `.pegou` e a forma ENDERECADA. Nao remova nem
  altere o comportamento de `.corrigir`.

**Fora de escopo:** `.gsd/` nao entra em commit nenhum (esta sem rastreamento e
nao pertence a esta tarefa).
</decisions_travadas>

<discricao_do_claude>
Decisoes que o usuario deixou em aberto e que eu tomei ao ler o codigo. Estao
aqui para o executor NAO reabri-las e para o SUMMARY registra-las.

**1. Coexistencia confirmada, e o argumento nao e "ja estava assim".** Li o
`corrigir` inteiro. `.pegou` SUBSUME `.corrigir` em funcionalidade — sempre da
para digitar o horario do ultimo boss —, mas nao em seguranca. A regra 3 da
docstring de `corrigir` (`loot.py:307`) diz que o raio de estrago e limitado
por DESENHO, nao por cuidado de quem digita: nao existe sintaxe que alcance
historico arbitrario. `.pegou` cria essa sintaxe de proposito, e paga por ela
com uma protecao diferente — o encaixe obrigatorio na agenda (D-02) e a
resposta que sempre diz o dia (D-01). Os dois limites sao reais e sao
diferentes. Unificar significaria escolher um so, e o `.corrigir` sem argumento
nenhum e justamente o que nao da para digitar errado no meio de um farm.
Coexistem, e o enum precisa dizer isso em comentario.

**2. Tolerancia do encaixe: 30 minutos, desempate pela ocorrencia mais cedo.**
O Solo Boss nasce de duas em duas horas, entao qualquer minuto do dia esta a no
maximo 60 min de alguma ocorrencia — uma tolerancia de 60 nunca recusaria nada
e transformaria D-02 em decoracao. 30 minutos aceita `.pegou 18:20` como o boss
das 18:00 (o caso real: a pessoa lembra depois) e RECUSA `.pegou 19:00`, que e
ambiguo entre 18:00 e 20:00. Ambiguidade recusa; e o unico desfecho honesto
quando o registro e permanente.

**3. Uma gramatica so, morando em `loot.py`.** `interpretar_pegou` e escrita em
`loot.py` e IMPORTADA por `comandos.py` como portao do parser. Duas gramaticas
— uma que valida no parser e outra que le no responder — divergem no primeiro
ajuste e o comando passa a aceitar o que nao sabe executar. O preco e um parse
duplicado por comando (uma vez por mensagem, uma vez por semana): irrelevante.

**4. `NICK_VALIDO` muda de casa, de `comandos.py` para `loot.py`.** Consequencia
direta de (3): `interpretar_pegou` precisa validar nick e `loot.py` nao pode
importar `comandos` (`loot.py:27` — ciclo). `comandos.py` ja importa `apelido`
de `loot`, entao a direcao da dependencia ja existe e nao inverte nada.
`comandos.py` passa a fazer `_NICK_VALIDO = NICK_VALIDO` com o import, e o
comentario que explica o charset e o minimo de 2 caracteres MUDA JUNTO — nao
fica orfao no arquivo antigo. Zero mudanca de comportamento; os testes atuais
de `.loot-a` e `.corrigir-a` continuam valendo sem edicao.

**5. `_ocorrencias` vira publica como `ocorrencias_do_dia`.** O encaixe precisa
enumerar ocorrencias PASSADAS e nao existe funcao para isso — `proxima_ocorrencia`
so olha para frente. Publicar a que ja existe e menos codigo e menos divergencia
do que uma segunda enumeracao dentro de `loot.py`. Sao 4 chamadas internas em
`agenda.py` para renomear; nenhum teste referencia o nome privado (verificado
por grep).

**6. `atribuir` SOLTA a designacao pendente quando ela mira o MESMO alvo, e so
nesse caso.** Este e o unico ponto onde eu encosto na fronteira que a tarefa
anterior recusou atravessar ("cancelar e sobre a VEZ, `.corrigir` e sobre o
HISTORICO"). O motivo e concreto: se o scanner estava fora do ar as 18:00, a
designacao das 18:00 continua em `proximo.json` sem ter sido consumida. O
usuario roda `.pegou 18:00 Korzis`, e no tick seguinte o `consumir()` cria um
SEGUNDO dono para as 18:00 — um duplicado que o usuario nao pediu e que aparece
na contagem de quem nao pegou nada. A regra e estreita e nao mistura conceito:
uma designacao cujo boss ja passou E ja tem dono escrito a mao nao tem mais
alvo. Compare `designacao.alvo == alvo` exato; qualquer outra designacao fica
INTACTA. Registre isso na docstring e num teste com nome proprio.

**7. Uma mensagem so para "data que nao aponta para momento nenhum".** Data no
futuro (`.pegou 30/12 18:00 X` em agosto) e data impossivel (`31/02`) recebem o
MESMO texto, porque o texto e verdadeiro nos dois casos: aquela data nao aponta
para nenhum momento que ja passou. Nao invente duas mensagens nem um segundo
canal de erro para distinguir — `momento_desejado` devolve `datetime | None` e
so.
</discricao_do_claude>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: o caminho inteiro do `.pegou <hora> <nick>`, de ponta a ponta</name>
  <files>tests/test_loot.py, tests/test_comandos.py, l2scanner/agenda.py, l2scanner/loot.py, l2scanner/comandos.py, l2scanner/__main__.py</files>
  <read_first>
    - `l2scanner/loot.py` linhas 115-200 (`RegistroDeLoot.__init__`, `_criar`, `_nome_do_pegou`, `registrar`, `registros`, `resumo`) — as primitivas exatas que `atribuir` compoe; o tri-estado do `_criar` e o motor de D-05.
    - `l2scanner/loot.py` linhas 287-347 (`corrigir`) — o metodo que `atribuir` espelha. As tres regras da docstring (ordem, guarda do mesmo apelido, raio de estrago) sao a especificacao de D-05, escritas por extenso.
    - `l2scanner/loot.py` linhas 377-390 (`descrever_momento`) — o formatador de D-01. NAO escreva outro.
    - `l2scanner/loot.py` linhas 515-570 (`responder_correcao`) — o molde exato de uma funcao `responder_*` e do texto que nomeia o que mudou.
    - `l2scanner/agenda.py` linhas 75-135 (`EventoAgendado`, `_ocorrencias`) e 185-205 (`proxima_ocorrencia`) — a estrutura `horarios: tuple[tuple[int, int], ...]` e o padrao de varredura por dia.
    - `l2scanner/comandos.py` linhas 207-309 (`_NICK_VALIDO`, `_PALAVRAS_DE_CANCELAMENTO`, `interpretar_dinamico`) — os ramos `loot`/`corrigir` que o `.pegou` copia, e o `return None` de `comandos.py:299` que e a licao de D-04.
    - `l2scanner/__main__.py` linhas 558-600 (os quatro ramos de loot em `atender_comandos`).
    - `tests/test_comandos.py` linhas 727-790 (`TestLootNaCostura._atender`) — o `LeitorFalso` e o helper que a costura reusa; ele ja monta um `EventoAgendado` de Solo Boss de duas em duas horas e um `agora` de `2026-08-25 09:05`.
  </read_first>
  <behavior>
    RED primeiro. Escreva estes tres testes, veja falhar, so entao implemente.

    Em `tests/test_loot.py`, numa classe nova `TestAtribuicaoEnderecada` depois
    de `TestCorrecao`:

    - **registrar um boss que nao tinha registro nenhum.** Pasta vazia. Chame
      `responder_atribuicao(registro, [SOLO], em(18, 30), "18:00 Korzis")`.
      Afirme: `registro.resumo("Korzis") == (1, em(18, 0))`,
      `len(registro.registros()) == 1`, e a resposta contem "Korzis", "18:00" e
      "hoje". Este e o teste do problema que o usuario relatou — ele falha hoje
      porque nao existe caminho nenhum, nao porque o caminho esta errado.

    - **o horario gravado e o do BOSS, nao o digitado (D-02).** Chame com
      `"18:20 Korzis"` as 18:30. Afirme que o unico registro tem alvo
      `em(18, 0)` — nao `em(18, 20)`. Sem isto, a estatistica ganharia um
      horario que nenhuma consulta futura por horario de boss encontraria.

    - **sem boss por perto, RECUSA e nao grava (D-02).** Chame com
      `"19:00 Korzis"` as 19:30 — 60 minutos de distancia dos dois bosses
      vizinhos, ambiguo. Afirme que `registro.registros() == []` e que a
      resposta contem "19:00" e pelo menos dois dos horarios configurados
      ("18:00" e "20:00"). Escreva na docstring do teste que registro orfao e
      permanente: nunca ha poda, entao a recusa e mais barata que a limpeza.

    Em `tests/test_comandos.py`, dentro de `TestInterpretarDinamico`:

    - `.pegou 18:00 Korzis` devolve `(Comando.LOOT_ATRIBUIR, "18:00 Korzis")`.
    - `.pegou` SOZINHO devolve `None`, e `.pegou` com
      `nicks_conhecidos=frozenset({"pegou"})` TAMBEM devolve `None` — a prova
      direta de que o ramo fecha a porta do nick homonimo (D-04).

    Em `tests/test_comandos.py`, dentro de `TestLootNaCostura` — a costura, que
    e onde os erros deste projeto moram:

    - **`.pegou 08:00 Korzis` atravessa parser, dispatch e disco.** O helper
      `_atender` roda com `agora = 2026-08-25 09:05`, entao o boss das 08:00 ja
      passou. Crie um `RegistroDeLoot(tmp_path / "loot")` vazio, chame
      `self._atender(tmp_path, ".pegou 08:00 Korzis", loot)`. Afirme que os
      destinos sao so `["1"]` (sem eco no grupo), que a resposta contem
      "Korzis", e que `loot.resumo("Korzis") == (1, datetime(2026, 8, 25, 8, 0))`.
  </behavior>
  <action>
    Implemente o caminho fino inteiro — agenda, resolucao, disco, texto, parser
    e dispatch — numa passada so, para que `.pegou <hora> <nick>` funcione de
    ponta a ponta antes de qualquer variacao de sintaxe entrar. Data explicita
    e grafias alternativas de horario sao do Task 3; a ASSINATURA das funcoes
    ja nasce preparada para elas aqui, para o Task 3 preencher sem rearquitetar.

    **`l2scanner/agenda.py` — publicar a enumeracao por dia.** Renomeie
    `_ocorrencias` para `ocorrencias_do_dia` e atualize as quatro chamadas
    internas (linhas ~157, ~200, ~402, ~476). Acrescente uma linha a docstring
    dizendo que ela e publica porque o encaixe do `.pegou` precisa enumerar
    ocorrencias PASSADAS, e `proxima_ocorrencia` so olha para frente. Nao mude
    o corpo.

    **`l2scanner/comandos.py` -> `l2scanner/loot.py` — mudar `NICK_VALIDO` de
    casa.** Mova a constante e o comentario que a explica (o charset do L2, e o
    minimo de 2 para que `.loot-a` de um dedo escorregado nao vire designacao)
    para `loot.py`, com o nome publico `NICK_VALIDO`. Em `comandos.py`,
    importe-a junto de `apelido` e faca `_NICK_VALIDO = NICK_VALIDO`, com uma
    linha dizendo que o nome privado sobrevive porque os seis usos do arquivo
    ja falam essa lingua, e que a definicao mora em `loot` porque
    `interpretar_pegou` precisa dela e `loot` nao pode importar `comandos`. NAO
    edite os seis usos nem os testes existentes: o comportamento nao muda.

    **`l2scanner/loot.py` — `PedidoDePegou`** (frozen, ao lado de `Correcao`):
    campos `nick: str`, `hora: int`, `minuto: int`, `dia: int | None = None`,
    `mes: int | None = None`, `ano: int | None = None`. Docstring: e o `.pegou`
    DEPOIS da gramatica e ANTES do relogio — nenhum `datetime` aqui, porque a
    mesma disciplina do modulo manda o tempo entrar por parametro, e e isso que
    permite testar a virada da meia-noite sem esperar meia-noite.

    **`l2scanner/loot.py` — `interpretar_pegou(argumento: str) -> PedidoDePegou | None`**:
    funcao pura. Recebe o argumento ja sem o `.pegou`. Divide em palavras.
    Nesta task aceita SOMENTE a forma de duas palavras `[hora, nick]`; qualquer
    outra contagem devolve `None`. O horario aceita `HH:MM` (as outras grafias
    entram no Task 3); valide hora 0-23 e minuto 0-59 NUMERICAMENTE depois do
    casamento, em vez de espremer faixas dentro da expressao regular — este
    arquivo prefere linha legivel a expressao esperta. O nick passa por
    `NICK_VALIDO.fullmatch` e e preservado COMO FOI DIGITADO. Docstring
    explicando que esta funcao e o PORTAO do parser (o `comandos.py` so
    reconhece o comando quando ela aceita) e o LEITOR do responder — uma
    gramatica so, porque duas divergem no primeiro ajuste e o comando passa a
    aceitar o que nao sabe executar.

    Nao acrescente palavras reservadas aqui. `.pegou` nao tem forma destrutiva
    sem argumento, entao nao existe a colisao que obrigou o
    `_PALAVRAS_DE_CANCELAMENTO` a nascer — escreva isso numa linha, do mesmo
    jeito que a docstring do ramo `corrigir-` ja escreve.

    **`l2scanner/loot.py` — `momento_desejado(pedido, agora) -> datetime | None`**:
    o instante que o usuario quis dizer. Sem data (D-01): monte
    `agora.replace(hour=..., minute=..., second=0, microsecond=0)` e, se ficar
    DEPOIS de `agora`, recue um dia. Esse recuo de uma linha e D-01 inteiro: as
    02h, "18:00" e ontem. Com data (Task 3) devolve `None` por enquanto — deixe
    o ramo escrito e comentado apontando para o Task 3, nao um `TODO` vago.
    Docstring com o exemplo das 02h por extenso.

    **`l2scanner/loot.py` — `encaixar_na_agenda(desejado, eventos, agora) -> datetime | None`**:
    acha o `EventoAgendado` do Solo Boss por `eh_solo_boss` (None se nao houver)
    e varre `ocorrencias_do_dia` para os dias `desejado.date() - 1`,
    `desejado.date()` e `desejado.date() + 1`. Tres dias centrados no DESEJADO,
    nao em `agora`: e o que faz a virada da meia-noite funcionar nos dois
    sentidos e o que permite uma data explicita antiga (Task 3) sem janela de
    busca arbitraria. Descarte qualquer ocorrencia com `alvo > agora` — D-01
    proibe resolver para o futuro, e essa e a linha que garante. Escolha
    `min(candidatas, key=lambda alvo: (abs(alvo - desejado), alvo))` — o
    desempate pela ocorrencia mais CEDO e deterministico de proposito, para que
    duas chamadas iguais escolham o mesmo registro. Devolva `None` quando a
    distancia da melhor candidata passar de `TOLERANCIA_DE_ENCAIXE`.

    Defina `TOLERANCIA_DE_ENCAIXE = timedelta(minutes=30)` como constante de
    modulo, com o comentario que justifica o numero: o boss nasce de duas em
    duas horas, entao qualquer minuto do dia esta a no maximo 60 min de alguma
    ocorrencia e uma tolerancia de 60 nunca recusaria nada — D-02 viraria
    decoracao. 30 aceita "lembrei 20 minutos depois" e recusa 19:00, que e
    ambiguo entre dois bosses. Ambiguidade recusa, porque o registro e
    permanente.

    **`l2scanner/loot.py` — `horarios_do_solo_boss(eventos) -> list[str]`**:
    devolve `["00:00", "02:00", ...]` ordenado, do `EventoAgendado` do Solo
    Boss; lista vazia quando nao ha evento. Existe para a mensagem de recusa de
    D-02 — recusar sem dizer quais horarios valem obriga a pessoa a abrir o
    `config.toml` no meio do farm.

    **`l2scanner/loot.py` — quinto estado em `Correcao`.** Acrescente
    `"criado"` a lista de valores de `estado` no comentario do campo E na
    docstring da dataclass, explicando que o quinto estado nasceu com o
    `.pegou`: `corrigir` nunca cria registro (so troca dono), `atribuir` cria
    quando nao havia nada, e "criei do zero" nao pode sair com o mesmo texto de
    "troquei o dono" pelo mesmo motivo que os outros quatro nao podem —
    colapsar faz o bot mentir sobre o que acabou de acontecer com a
    estatistica. `anterior` fica `""` neste estado, e a mensagem correspondente
    nao pode chamar `exibir(anterior)`.

    **`l2scanner/loot.py` — `RegistroDeLoot.atribuir(nick, alvo) -> Correcao`**:
    metodo novo depois de `corrigir`. NUNCA levanta, NUNCA devolve None. Passos:

    1. `donos = sorted(slug for slug, quando in self.registros() if quando == alvo)`
       e `slug_novo = apelido(nick)`.
    2. **Sem dono nenhum:** `estado = self._criar(self._nome_do_pegou(nick, alvo))`.
       `"falhou"` devolve `Correcao("falhou", novo=nick, alvo=alvo)`. Caso
       contrario cria o marcador `nick_*`, solta a designacao do passo 6 e
       devolve `Correcao("criado", novo=nick, alvo=alvo)`.
    3. **A GUARDA (D-05):** `if donos == [slug_novo]:` devolve
       `Correcao("mesmo_dono", anterior=slug_novo, novo=nick, alvo=alvo)` sem
       tocar em disco. Note que a comparacao e com a lista INTEIRA, nao com o
       primeiro elemento: quando ha duplicado no mesmo alvo e um dos donos ja e
       o nick novo, o caminho certo e seguir para o passo 4 e deixar o passo 5
       colapsar o duplicado — sair cedo ali deixaria o duplicado de pe.
    4. `anterior = next(d for d in donos if d != slug_novo)`;
       `estado = self._criar(self._nome_do_pegou(nick, alvo))` — CRIAR ANTES
       (D-05). `"falhou"` devolve `Correcao("falhou", anterior=anterior, ...)`
       sem apagar nada.
    5. So agora apaga o velho:
       `(self._pasta / self._nome_do_pegou(anterior, alvo)).unlink(missing_ok=True)`,
       dentro de `try/except OSError` que segue em frente. Um `"ja_existia"` no
       passo 4 chega aqui DE PROPOSITO: ele so acontece quando o alvo tinha
       dois donos, e apagar o velho e o conserto, nao a perda.
    6. Cria o marcador `nick_*` (idempotente) e chama o helper
       `_soltar_designacao(alvo)`. Devolve `Correcao("corrigido", ...)`.

    **`l2scanner/loot.py` — `RegistroDeLoot._soltar_designacao(alvo)`**: le a
    designacao corrente e, SO SE `designacao.alvo == alvo` exato, apaga
    `proximo.json` com `missing_ok=True`. Docstring com o motivo por extenso —
    e o unico ponto deste trabalho que encosta na fronteira entre a VEZ e o
    HISTORICO, e ele so atravessa nesse caso: se o scanner estava fora do ar as
    18:00, a designacao das 18:00 continua pendente, e depois do `.pegou` o
    proximo `consumir()` criaria um SEGUNDO dono para as 18:00. Uma designacao
    cujo boss ja passou e ja tem dono escrito a mao nao tem mais alvo. Qualquer
    outra designacao fica intacta, e a comparacao exata e o que garante isso.

    A docstring de `atribuir` precisa dizer o PORQUE de tres coisas, no estilo
    do modulo: a ordem criar-antes-de-apagar com os tres desfechos escritos
    (nada muda / duplicado consertavel / loot perdido em silencio); a guarda da
    lista inteira e por que ela nao e a mesma guarda do `corrigir`; e a
    diferenca de alcance entre `atribuir` (alvo ENDERECADO, encaixado na
    agenda) e `corrigir` (o mais recente, sem argumento) — os dois limites sao
    reais e sao diferentes, e por isso os dois comandos coexistem (D-09).

    **`l2scanner/loot.py` — `responder_atribuicao(registro, eventos, agora, argumento) -> str`**:
    funcao pura no fim do arquivo, depois de `responder_correcao`, mesmo molde
    e tempo por parametro. Orquestra, nesta ordem, e cada `None` tem texto
    proprio:

    1. `interpretar_pegou(argumento)` -> `None`: resposta defensiva dizendo que
       nao entendeu, com um exemplo da forma certa. Nao deveria acontecer (o
       parser ja filtrou), e existe porque D-06 proibe confiar.
    2. `eh_solo_boss` nao acha evento: "Nao achei o Solo Boss na agenda do
       config.toml — nao da para registrar o loot." (mesmo texto-molde de
       `responder_designacao`).
    3. `momento_desejado(...)` -> `None`: aquela data nao aponta para nenhum
       momento que ja passou, e o `.pegou` so registra boss que ja aconteceu.
       UMA mensagem so, valida para data futura e para data impossivel.
    4. `encaixar_na_agenda(...)` -> `None`: recusa nomeando o horario digitado
       e listando `horarios_do_solo_boss(eventos)`.
    5. Caso contrario chama `registro.atribuir(pedido.nick, alvo)` e traduz o
       estado, com `momento = descrever_momento(alvo, agora)` (D-01) e o nome
       do evento saindo do `config.toml` com recurso a "Solo Boss", igual as
       outras tres funcoes `responder_*`:
       - `"criado"`: ninguem tinha registrado o loot daquele boss e agora ele e
         do novo dono;
       - `"corrigido"`: o loot daquele boss passou do antigo para o novo,
         nomeando os dois;
       - `"mesmo_dono"`: aquele loot JA era dele e nada mudou;
       - `"falhou"`: nao conseguiu gravar — dizendo que continua do antigo
         quando havia antigo, e que nada foi registrado quando nao havia.

    A docstring precisa registrar D-01 com todas as letras: a resposta sempre
    diz o DIA de volta porque o `.pegou` alcanca horario arbitrario, e o dia e
    exatamente a informacao que falta quando o alvo e o de ontem — a mesma
    razao que `responder_correcao` ja documenta em `loot.py:532`.

    **`l2scanner/comandos.py` — `Comando.LOOT_ATRIBUIR = "loot_atribuir"`**:
    novo membro junto dos outros de loot. O comentario precisa dizer que ele e
    o segundo comando que reescreve HISTORICO, e como o limite dele difere do
    `LOOT_CORRIGIR`: o `.corrigir` e limitado por nao ter sintaxe para alcancar
    o passado, o `.pegou` tem essa sintaxe e paga com o encaixe obrigatorio na
    agenda e com a resposta que sempre diz o dia (D-09).

    **`l2scanner/comandos.py` — os dois ramos em `interpretar_dinamico`**,
    depois dos ramos de `corrigir`:

    - `if crua.lower() == "pegou":` monta `argumento = " ".join(palavras[1:])`,
      devolve `(Comando.LOOT_ATRIBUIR, argumento)` quando
      `interpretar_pegou(argumento)` nao e `None`, e `return None` em qualquer
      outro caso.
    - O ramo com hifen `.pegou-<hora> <nick>` entra no Task 3.

    O `return None` do ramo e obrigatorio e nao e redundancia — copie o motivo
    de `comandos.py:291` adaptado: sem ele o fluxo cai no ramo de consulta logo
    abaixo, onde `_NICK_VALIDO` casa a palavra "pegou" e um nick homonimo
    transformaria o comando numa consulta. Nao acrescente "pegou" ao
    `_VOCABULARIO`: o vocabulario fixo tem precedencia sobre o dinamico e
    capturaria `.pegou` antes de `interpretar_dinamico` ver o argumento.

    Atualize tambem o comentario do campo `argumento` de `MensagemDeComando`
    (hoje diz "o nick, COMO FOI DIGITADO"): ele passa a carregar tambem o
    argumento inteiro do `.pegou`, ainda cru, ainda como digitado.

    **`l2scanner/__main__.py`**: importe `responder_atribuicao` do `.loot` e
    acrescente o ramo `elif pedido.comando is Comando.LOOT_ATRIBUIR:` junto dos
    outros, com o mesmo guarda-chuva `if loot is None` e `avisar_o_grupo = False`.
    O comentario do ramo diz o motivo PROPRIO dele, nao "igual ao de cima":
    registrar loot de boss passado e conserto de contabilidade entre quem ja
    sabe o que aconteceu, e a confirmacao com o dia so serve para quem digitou
    conferir se acertou o boss.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_loot.py tests/test_comandos.py tests/test_agenda.py -q</automated>
  </verify>
  <done>`.pegou 08:00 Korzis` atravessa parser, dispatch, disco e resposta: o registro nasce no horario do BOSS mesmo sem designacao previa, a resposta nomeia o Korzis e o dia, e um horario sem boss por perto recusa sem gravar nada.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: as invariantes que protegem a estatistica, e a virada da meia-noite</name>
  <files>tests/test_loot.py, l2scanner/loot.py</files>
  <read_first>
    - `tests/test_loot.py` linhas 124-140 (`test_falha_de_disco_MANTEM_a_designacao`) — o padrao de `monkeypatch` sobre `_criar` que este task reusa para simular disco cheio.
    - `tests/test_loot.py` linhas 557-720 (`TestCorrecao`) — os nomes e o estilo dos testes de invariante que este task espelha para `atribuir`.
    - `l2scanner/loot.py` — o `atribuir`, o `_soltar_designacao`, o `momento_desejado` e o `encaixar_na_agenda` escritos no Task 1.
  </read_first>
  <behavior>
    Alguns destes testes podem passar de primeira, porque o Task 1 ja
    implementou o mecanismo — isso e esperado e NAO e desculpa para pular
    nenhum. Eles sao a armadura contra regressao, e uma propriedade que protege
    estatistica sem backup precisa de um teste com nome proprio para sobreviver
    ao proximo refactor. Se algum deles revelar um furo no Task 1, conserte o
    CODIGO, nunca o teste.

    Em `tests/test_loot.py`, na classe `TestAtribuicaoEnderecada`:

    - **as 02h, "18:00" e ONTEM (D-01).** `agora = em(2, 30, dia=25)`,
      argumento `"18:00 Korzis"`. Afirme que o registro nasceu em
      `em(18, 0, dia=24)` e que a resposta contem "ontem". Este e o teste que o
      usuario pediu nominalmente.

    - **a virada da meia-noite no sentido contrario.** `agora = em(0, 10)`,
      argumento `"23:50 Korzis"`. O desejado e 23:50 de ontem, mas a ocorrencia
      mais proxima que ja passou e a de HOJE as 00:00 (10 minutos depois do
      desejado, contra 110 minutos do boss das 22:00 de ontem). Afirme que o
      alvo e `em(0, 0, dia=25)`. Este e o teste que prova que a busca do
      encaixe e centrada no DESEJADO e nao em `agora`, e ele falha de forma
      silenciosa e permanente se alguem "simplificar" a varredura de tres dias.

    - **nunca resolve para o futuro (D-01).** `agora = em(17, 0)`, argumento
      `"18:00 Korzis"`. Afirme que o alvo e o de ONTEM (`em(18, 0, dia=24)`) e
      nao o de hoje daqui a uma hora, e que a resposta contem "ontem".

    - **o encaixe aceita o atraso de quem lembrou depois.** `"18:20 Korzis"` as
      18:40 encaixa em `em(18, 0)`; `"17:45 Korzis"` as 19:00 tambem encaixa em
      `em(18, 0)` — a ocorrencia mais proxima pode estar DEPOIS do horario
      digitado, contanto que ja tenha passado.

    - **a recusa lista os horarios (D-02).** `"19:00 Korzis"` recusa e a
      resposta contem "18:00" e "20:00". Com uma agenda de Solo Boss so de
      `("08:00", "20:00")`, `"14:00"` recusa e a resposta lista exatamente
      esses dois. Nada e gravado em nenhum dos casos.

    - **agenda sem Solo Boss nao levanta (D-06).** Chame com `eventos=[]` e com
      uma lista contendo so um `EventoAgendado` de TvT. Resposta honesta,
      `registros()` vazio, zero excecao.

    - **a troca enderecada alcanca um boss que NAO e o mais recente (D-03).**
      Registre `pegou_` para "TioMad" as 08:00 e para "Kaus" as 18:00. Chame
      `.pegou 08:00 Korzis`. Afirme que o das 08:00 virou do Korzis e que o das
      18:00 continua do Kaus. Este e o teste que mostra o que `.pegou` faz e
      `.corrigir` nao consegue fazer (D-09) — escreva isso na docstring do
      teste.

    - **atribuir ao dono que ja e o dono nao apaga nada (D-05).** Registre
      `pegou_` para "Korzis" as 18:00, chame `registro.atribuir("KORZIS", em(18, 0))`
      — caixa diferente, MESMO `apelido()`. Afirme estado `"mesmo_dono"` e que
      `resumo("Korzis")` continua `(1, em(18, 0))`. Este teste falha de forma
      DESTRUTIVA se a guarda faltar.

    - **sobra sempre pelo menos um `pegou_` para aquele alvo, em TODOS os
      desfechos.** Rode os quatro estados (criado, corrigido, mesmo_dono, e
      falhou com `_criar` monkeypatchado para `"falhou"`) e afirme, em cada um
      que tinha registro antes, que ainda existe algum `(slug, alvo)` com
      aquele alvo. E a forma sempre-verdadeira da invariante: o dono pode
      mudar, o loot nunca some.

    - **falha de disco NAO apaga o velho (D-05).** `_criar` monkeypatchado para
      `"falhou"`: `atribuir("Kaus", em(18, 0))` devolve estado `"falhou"`,
      "TioMad" continua com o loot, "Kaus" continua com zero, e a resposta diz
      que o loot continua do antigo.

    - **o duplicado colapsa.** Registre `pegou_` para "tiomad" E para "korzis"
      no MESMO alvo — o estado que sobra quando um apagar falhou. Chame
      `atribuir("Korzis", alvo)`. Afirme que sobra exatamente um registro
      naquele alvo e que ele e do Korzis. Comente que isto e o conserto do
      duplicado, e que sair cedo pela guarda do `mesmo_dono` aqui deixaria o
      duplicado de pe.

    - **a designacao pendente do MESMO alvo e solta; a de outro alvo NAO
      (discricao 6).** Designe "TioMad" para `em(18, 0)`, chame
      `.pegou 18:00 Korzis` as 18:30, e afirme que `registro.designacao()` e
      `None` — senao o proximo `consumir()` criaria um segundo dono para as
      18:00. Depois, num registro limpo, designe "TioMad" para `em(20, 0)`,
      chame `.pegou 18:00 Korzis` as 18:30, e afirme que a designacao das 20:00
      continua INTACTA.
  </behavior>
  <action>
    Ajuste `atribuir`, `_soltar_designacao`, `momento_desejado`,
    `encaixar_na_agenda` e os textos de `responder_atribuicao` ate os testes
    passarem sem afrouxar nenhuma assercao.

    Nao acrescente parametro novo, nao troque a assinatura de `atribuir` e nao
    crie um caminho que grave sem passar por `encaixar_na_agenda`. D-02 e o que
    impede registro orfao permanente, e ele nao se negocia porque um teste
    ficou mais dificil de montar.

    Se a varredura de tres dias centrada no desejado parecer excessiva ao ler o
    codigo pronto, releia o teste da virada da meia-noite antes de encolher:
    ele e a razao de ela existir.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_loot.py -q</automated>
  </verify>
  <done>Os cinco estados de `Correcao` produzidos por `atribuir` tem teste proprio; a virada da meia-noite passa nos dois sentidos; a recusa lista os horarios; a designacao pendente do mesmo alvo e solta e a de outro alvo nao.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: a gramatica completa, as portas dos fundos, e o README</name>
  <files>tests/test_comandos.py, tests/test_loot.py, l2scanner/loot.py, l2scanner/comandos.py, README.md</files>
  <read_first>
    - `l2scanner/loot.py` — `interpretar_pegou` e `momento_desejado` escritos no Task 1, em especial o ramo de data explicita deixado apontando para este task.
    - `l2scanner/comandos.py` linhas 253-309 (os ramos de `loot` e `corrigir` em `interpretar_dinamico`) — o par hifen/espaco que o `.pegou` completa aqui.
    - `tests/test_comandos.py` linhas 101-286 (`TestInterpretarDinamico`) — onde os testes entram e os nomes que a classe ja usa.
    - `README.md` linhas 285-300 — a tabela de comandos, que hoje lista `.cancelar` e `.status` e NENHUM comando de loot.
  </read_first>
  <behavior>
    RED primeiro. Estes testes falham hoje: nem a data explicita, nem as
    grafias alternativas de horario, nem o ramo com hifen existem.

    Em `tests/test_loot.py`, na classe `TestAtribuicaoEnderecada`:

    - **data explicita alcanca um dia antigo (D-01).** `agora = em(10, 0, dia=25)`,
      argumento `"23/08 18:00 Korzis"`. Afirme que o alvo e
      `datetime(2026, 8, 23, 18, 0)` e que a resposta contem "23/08" — o
      formato de `descrever_momento` para mais de um dia atras.
    - **data explicita com ano de quatro digitos** (`"23/08/2026 18:00 Korzis"`)
      chega no mesmo alvo.
    - **data explicita no FUTURO recusa e nao grava.** Em 25/08, argumento
      `"30/12 18:00 Korzis"`. Afirme `registros() == []`. A mesma resposta vale
      para `"31/02 18:00 Korzis"`, que nao aponta para momento nenhum — uma
      mensagem so para os dois casos, por discricao 7.
    - **a virada do ano.** `agora = datetime(2027, 1, 3, 10, 0)`, argumento
      `"30/12 18:00 Korzis"` sem ano: o alvo e 30/12/**2026**, nao 30/12/2027.
      Sem o recuo de um ano, dezembro seria sempre uma data futura em janeiro.
    - **as grafias de horario.** `"18h Korzis"`, `"18h00 Korzis"`,
      `"18h30 Korzis"` e `"18 Korzis"` resolvem para o mesmo boss que
      `"18:00 Korzis"` resolveria (com `18h30` encaixando em 18:00 pela
      tolerancia). O usuario escreveu "boss das 18h" ao relatar o problema —
      essa e a grafia que ele usa.

    Em `tests/test_comandos.py`, dentro de `TestInterpretarDinamico`:

    - `.pegou-18:00 Korzis` devolve `(Comando.LOOT_ATRIBUIR, "18:00 Korzis")` —
      a mesma coisa que a forma de duas palavras (D-04).
    - `.pegou-24/08 18:00 Korzis` devolve o argumento com as tres partes.
    - `.PEGOU 18:00 Korzis` funciona: o comando e case-insensitive e o nick e
      preservado como digitado.
    - Devolvem `None`: `.pegou 18:00` (sem nick), `.pegou Korzis` (sem hora),
      `.pegou 18:00 a` (nick curto demais), `.pegou 18:00 j4;rm` (charset),
      `.pegou 25:00 Korzis` (hora invalida), `.pegou-` e `.pegou 18:00 20:00 Korzis`.
    - Regressao: `.loot-j4guar`, `.loot`, `.loot cancelar`, `.corrigir-kaus`,
      `.corrigir kaus` e `.corrigir` continuam devolvendo exatamente o que
      devolviam. O comando novo nao pode ter deslocado nenhum ramo existente.
  </behavior>
  <action>
    **`l2scanner/loot.py` — completar `interpretar_pegou`.** Aceite tambem a
    forma de tres palavras `[data, hora, nick]`. A data casa
    `DD/MM` ou `DD/MM/AAAA` (aceite tambem dois digitos de ano, virando
    `2000 + aa`), com dia 1-31 e mes 1-12 validados numericamente; a existencia
    real da data (30/02) so pode ser decidida com o ano em maos e fica com
    `momento_desejado`. O horario passa a aceitar `HH:MM`, `HHhMM`, `HHh` e
    `HH` — uma expressao regular so, com as faixas validadas em linha separada.
    Qualquer contagem de palavras diferente de 2 ou 3 devolve `None`.

    **`l2scanner/loot.py` — completar `momento_desejado`.** Com data: ano
    explicito quando houver; sem ano, tente `agora.year` e, se o instante ficar
    DEPOIS de `agora`, tente `agora.year - 1` — e o que faz "30/12" em janeiro
    apontar para dezembro passado. Construa o `datetime` dentro de
    `try/except ValueError` e devolva `None` quando a data nao existir (D-06:
    nunca levanta). Ainda no futuro depois do recuo: `None`. Escreva o exemplo
    da virada do ano na docstring — ele e a razao do recuo existir.

    **`l2scanner/comandos.py` — o ramo com hifen.** Antes do ramo
    `crua.lower() == "pegou"`, acrescente
    `if crua.lower().startswith("pegou-"):`, que monta o argumento juntando o
    resto do miolo com as palavras seguintes
    (`" ".join([crua[len("pegou-"):], *palavras[1:]]).strip()`) e devolve
    `(Comando.LOOT_ATRIBUIR, argumento)` quando `interpretar_pegou` aceita,
    `None` caso contrario. Um comentario de uma linha ligando o ramo a D-04 e a
    licao de `comandos.py:295`: a forma de duas palavras nunca e opcional num
    comando que mexe em estado duravel, e a de hifen tambem nao, porque a mao
    do usuario ja aprendeu `.loot-` e `.corrigir-`.

    **`README.md` — a tabela de comandos.** Ela lista `.cancelar` e `.status` e
    ignora a familia inteira de loot, que ja tem quatro comandos em producao.
    Acrescente, na mesma tabela e na mesma voz curta das duas linhas que ja
    existem:

    - `.loot-<nick>` — marca quem pega o loot do proximo Solo Boss
    - `.loot-` — desmarca (o aviso volta a sair sem nome)
    - `.<nick>` — quantos loots o char ja pegou, e quando foi o ultimo
    - `.corrigir-<nick>` — troca o dono do ultimo loot ja registrado
    - `.pegou <hora> <nick>` — registra quem pegou o loot de um boss que ja
      passou, mesmo sem ter sido marcado antes

    Logo abaixo da tabela, um paragrafo curto com o exemplo real e a diferenca
    entre os dois ultimos: `.pegou 18:00 Korzis` fala de um horario
    ESPECIFICO e serve quando ninguem tinha marcado nada, `.corrigir-Korzis`
    e o atalho para o boss que acabou de passar. Mencione que o horario e
    encaixado no boss mais proximo e que a resposta sempre diz o dia, para o
    usuario conferir que acertou o boss.
  </action>
  <verify>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest tests/test_comandos.py tests/test_loot.py -q</automated>
    <automated>cd "C:/Users/refun/Desktop/Lineage2-warnings" && python -m pytest -q</automated>
  </verify>
  <done>As tres sintaxes de D-04 registram, as formas incompletas e o nick homonimo nao registram, a data explicita alcanca dias antigos sem cair no futuro, os ramos de `.loot` e `.corrigir` seguem intactos, o README documenta a familia inteira e a suite esta verde.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WhatsApp -> Chatwoot -> `comandos_novos` | Texto de terceiro atravessa a rede e vira acao no scanner |
| `interpretar_pegou` -> `_nome_do_pegou` -> pasta `.loot/` | Texto de terceiro vira NOME DE ARQUIVO |
| `atribuir` -> pasta `.loot/` | Estado duravel que NUNCA e podado e nao tem backup |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pik-01 | Tampering | `.pegou` reescrevendo historico de loot arbitrario | high | mitigate | D-02: o alvo tem que ENCAIXAR numa ocorrencia real do Solo Boss dentro de 30 min, e `alvo <= agora`. Nao ha sintaxe que alcance um instante que a agenda nao produz. Cada `.pegou` move ou cria um unico registro. |
| T-pik-02 | Tampering | Registro orfao permanente num horario inventado | high | mitigate | `encaixar_na_agenda` devolvendo `None` RECUSA e nao grava (D-02); testado com horario ambiguo e com agenda sem Solo Boss. A pasta nunca e podada, entao a recusa e a unica limpeza que existe. |
| T-pik-03 | Tampering | Perda silenciosa de um `pegou_` no meio da troca | critical | mitigate | D-05: criar antes de apagar, guarda da lista inteira de donos, `try/except OSError` no apagar, e o teste de invariante do Task 2 que afirma que sobra um `pegou_` para o alvo nos quatro desfechos. |
| T-pik-04 | Elevation of Privilege | Nick virando path traversal no nome do arquivo | high | mitigate | `NICK_VALIDO` (`[A-Za-z0-9]{2,16}`) no portao do parser e `apelido()` (que colapsa tudo que nao e `[a-z0-9]` em hifen) antes de tocar em nome de arquivo. Sem barra, sem ponto, sem `..`, sem shell em ponto nenhum do caminho. |
| T-pik-05 | Spoofing | Qualquer um do grupo registrando loot no proprio nome | high | mitigate | Passa pelo mesmo `comandos_novos` das travas existentes: so `incoming`, nao `private`, dedupe por id de mensagem, allowlist de conversa e allowlist de telefone. Nenhum caminho novo de entrada e criado. |
| T-pik-06 | Denial of Service | Data absurda fazendo o scanner varrer meses de agenda | low | mitigate | `encaixar_na_agenda` varre TRES dias centrados no desejado, nunca um intervalo derivado da entrada do usuario. Custo constante independente do que foi digitado. |
| T-pik-07 | Tampering | npm/pip/cargo installs | n/a | accept | Nenhuma dependencia nova. Somente stdlib (`re`, `datetime`) e modulos ja no projeto. |
</threat_model>

<source_audit>
## Multi-Source Coverage Audit

| Fonte | Item | Plano | Task |
|-------|------|-------|------|
| GOAL | Registrar retroativamente quem pegou o loot de um boss que ja passou | 01 | 1-3 |
| CONTEXT | D-01 data opcional, resolve para o passado, resposta diz o dia | 01 | 1 (sem data) + 2 (ontem, meia-noite, nunca futuro) + 3 (data explicita) |
| CONTEXT | D-02 encaixe na agenda, horario da ocorrencia, recusa listando horarios | 01 | 1 (codigo + recusa) + 2 (testes de encaixe e recusa) |
| CONTEXT | D-03 unificado: cria quando nao ha, troca quando ha, mensagens distintas | 01 | 1 (codigo) + 2 (troca enderecada, cinco estados) |
| CONTEXT | D-04 duas formas, `.pegou` sozinho nao faz nada, nick homonimo | 01 | 1 (forma de espaco + `return None` + homonimo) + 3 (forma com hifen + formas invalidas) |
| CONTEXT | D-05 criar-antes-de-apagar, tri-estado, idempotencia entre instancias | 01 | 1 (codigo) + 2 (mutacao, disco falho, duplicado) |
| CONTEXT | D-06 nunca levanta no meio do farm | 01 | 1 (codigo) + 2 (agenda sem boss) + 3 (data impossivel) |
| CONTEXT | D-07 pt-BR, docstrings que justificam o porque | 01 | 1-3 (exigido em cada `<action>`) |
| CONTEXT | D-08 testes de gramatica, resolucao, encaixe, recusa e disco | 01 | 1-3 |
| CONTEXT | D-09 `.pegou` e `.corrigir` coexistem, com o porque registrado | 01 | 1 (enum + docstring) + 2 (teste do boss nao-recente) + 3 (README) |
| CONTEXT | Nao commitar `.gsd/` | 01 | fora de escopo, nenhum task encosta |
| RESEARCH | Stack fechado: stdlib + o que ja existe, zero dependencia nova | 01 | 1-3 (nenhum import externo) |
| RESEARCH | Config/estado em arquivo, sem hardcode de caminho novo | 01 | 1 (a pasta `.loot/` que ja existe) |

Nenhum item sem plano. Nenhum item adiado.
</source_audit>

<verification>
1. `python -m pytest -q` — a suite inteira verde, sem jogo aberto e sem rede.
   Baseline medida hoje: 683 testes coletados, `test_loot` + `test_comandos` +
   `test_agenda` com 205 passando.
2. `python -m pytest tests/test_loot.py -q -k Atribuicao` — os testes do
   `.pegou` isolados, para ler os nomes e conferir que D-01..D-09 estao
   cobertos.
3. Leitura do diff em `l2scanner/loot.py`: a linha do `unlink` vem DEPOIS da
   linha do `_criar`, existe retorno antecipado quando `donos == [slug_novo]`, e
   o `_soltar_designacao` compara `designacao.alvo == alvo` com igualdade
   exata. Sao as tres linhas onde este trabalho pode destruir dado.
4. `git status` antes do commit: `.gsd/` continua sem rastreamento e fora do
   commit.
</verification>

<success_criteria>
- `.pegou 18:00 Korzis` registra o loot do boss das 18:00 mesmo sem nunca ter
  havido designacao — o caso que o usuario relatou.
- As 02h, `.pegou 18:00 <nick>` fala do boss de ONTEM, e a resposta diz
  "ontem".
- O horario gravado e sempre o da ocorrencia do boss, nunca o digitado.
- Sem boss por perto, recusa nomeando os horarios que existem e nao grava nada.
- Registro existente com dono diferente troca de dono; sem registro, cria — com
  mensagens distintas, mais "ja era dele" e "o disco falhou".
- `.pegou <hora> <nick>` e `.pegou-<hora> <nick>` fazem a mesma coisa; `.pegou`
  sozinho nao faz nada nem vira consulta de um nick homonimo.
- Sobra sempre pelo menos um `pegou_` para o alvo, nos cinco desfechos.
- A designacao pendente do MESMO alvo e solta; a de qualquer outro alvo fica
  intacta.
- `.corrigir` continua funcionando exatamente como antes.
- README documenta a familia inteira de comandos de loot.
- A suite inteira passando, sem regressao nos 683 testes atuais.
</success_criteria>

<output>
Create `.planning/quick/260825-pik-adicionar-comando-pegou-horario-nick-par/260825-pik-SUMMARY.md` when done
</output>
