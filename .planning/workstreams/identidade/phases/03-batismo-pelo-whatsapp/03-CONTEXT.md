# Phase 3: Batismo pelo WhatsApp - Context

**Gathered:** 2026-08-31
**Workstream:** identidade
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 4 areas, 8 decisoes

<domain>
## Phase Boundary

O usuario da nome, do celular, a uma assinatura que o scanner APRENDEU — e so
consegue dar nome aquela que o scanner PERGUNTOU, nunca a "a linha 3 de agora".
A partir do batismo os alertas daquela pessoa saem com o nome certo.

DENTRO DA FASE: a pergunta que sai uma vez por assinatura aprendida, o pino que
prende a resposta aquela assinatura, o comando de batizar, a recusa de nome
duplicado, a correcao de um batismo errado, e o nome passando a valer sem
reiniciar.

FORA DA FASE: o OCR propor o nome (OCRB-01, v2). Esquecer uma entrada (adiado
na Fase 1). Mudar o reconhecimento — ele nao e tocado aqui.

</domain>

<decisions>
## Implementation Decisions

### Area 1: O pino, que e a peca onde um erro batiza a pessoa errada

- **D-01. O PINO E A CHAVE DE CONTEUDO DA ASSINATURA — o mesmo sha256 de 64
  hex que ja nomeia o arquivo no acervo.** Ele ja e estavel entre reinicios,
  independente da posicao e independente do nome (foi desenhado assim na Fase
  1, exatamente para esta fase poder apontar para ele). Nao existe pino novo a
  inventar; existe um pino a USAR.

- **D-02. O usuario nao digita 64 caracteres. A pergunta cita um APELIDO
  CURTO, e o apelido e um PREFIXO da propria chave.** Derivado, nao guardado:
  um mapa apelido->chave em disco seria um segundo estado que pode discordar do
  acervo, e a discordancia apareceria justamente no batismo. A resolucao e por
  prefixo contra as chaves presentes, e um prefixo AMBIGUO e RECUSADO com a
  lista dos candidatos — nunca resolvido no desempate. Prefixo desconhecido
  tambem e recusado, dizendo que ele nao existe.

- **D-03. A resposta NUNCA aceita posicao de linha como alvo.** Nao ha forma
  de escrever "batize a linha 3". A party se reorganiza entre a pergunta e a
  resposta — o usuario esta jogando, e a resposta chega minutos depois — e
  resolver por posicao batizaria a pessoa errada em SILENCIO, com a mensagem
  parecendo perfeitamente normal. E a mesma familia da mentira plausivel que o
  `identidade.py` inteiro existe para impedir. A posicao aparece na pergunta
  como AJUDA VISUAL ("vi na linha 4"), e nunca como identificador.

### Area 2: A pergunta que nao vira spam

- **D-04. UMA pergunta por assinatura, para sempre, marcada em disco no molde
  do `nome_<chave>`: um irmao `perguntado_<chave>` em `.identidades/`, criado
  com `O_CREAT|O_EXCL`.** A pasta e a certa por tres razoes que ja foram
  pagas: ela nao e podada (o `.agenda/` poda em 3 dias, e uma pergunta nao
  respondida em quatro dias voltaria a ser feita para sempre), ela e
  compartilhada pelas duas instancias (entao exatamente uma pergunta, e a
  outra recebe `ja_existia`), e ela e a mesma pasta que ja guarda a coisa
  perguntada.

  O marcador e a DECISAO, e nao uma checagem anterior — o mesmo desenho de
  `agenda.RegistroEmDisco.marcar` e de `respawn.anunciar_nascimento`. Uma
  checagem seguida de escrita perde a corrida entre as duas instancias.

- **D-05. Falha de disco ao marcar NAO manda a pergunta.** Aqui a assimetria e
  o contrario da agenda. La, aviso duplicado vence aviso perdido, e `OSError`
  colapsa em True. Aqui, uma pergunta perdida custa uma pessoa que continua
  como "Membro 4" ate o proximo aprendizado; uma pergunta REPETIDA custa o
  spam no grupo que o usuario ja reclamou uma vez neste projeto, e pode
  repetir para sempre, a cada tick, porque o marcador nunca chega ao disco.
  Perdido e recuperavel; laco infinito de mensagem no grupo nao e.

### Area 3: O nome

- **D-06. Batizar e criar/trocar o conteudo do irmao `nome_<chave>`, e a
  assinatura NAO e tocada.** E por isso que a chave nao muda quando o nome
  chega (Fase 1, D-03) e por isso que a correcao do BATI-05 e a MESMA
  operacao do batismo, e nao um caminho segundo. Um caminho segundo divergiria
  do primeiro na primeira vez que alguem mexesse num deles.

- **D-07. A recusa de nome duplicado (BATI-04) compara contra os
  `nome_<chave>` ja gravados, e a excecao e o proprio alvo.** Rebatizar a
  entrada X de "Kaus" para "Kaus" nao pode ser recusado como duplicata dela
  mesma, senao a correcao de acento ou de caixa fica impossivel. A resposta da
  recusa diz QUAL entrada ja tem o nome, com o apelido curto — sem isso o
  usuario nao tem como agir sobre a informacao.

- **D-08. O NOME PASSA A VALER NO MESMO TICK, sem reiniciar.** E o analogo
  direto do D-03 da Fase 2, e pela mesma razao: sem isso o batismo grava em
  disco e a tela continua dizendo "Membro 4" ate o proximo arranque, e o
  usuario batiza de novo achando que falhou. A lista viva de assinaturas
  recebe o nome; a assinatura em si nao muda, entao o reconhecimento nao e
  perturbado.

### Claude's Discretion

- Quantos digitos hex tem o apelido curto, e se ele aparece com algum
  delimitador na pergunta.
- O nome do comando e suas formas escritas no `_VOCABULARIO` (lembrar que ele
  TEM de entrar no `_AJUDA` — ha o tripwire `set(_AJUDA) == set(Comando)`).
- Se batizar e corrigir sao UM comando ou dois. O D-06 diz que a operacao e a
  mesma; se isso deve aparecer como um comando so e escolha de superficie.
- O texto exato da pergunta e das recusas.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/acervo.py`** — `AcervoDeIdentidades`, `chave_da_assinatura`,
  `_nome_de` (que ja le o irmao `nome_<chave>` e devolve `""` para qualquer
  coisa que nao seja um nick limpo), `NOME_VALIDO`. A leitura do nome JA
  EXISTE e ja e defensiva; falta a ESCRITA.
- **`l2scanner/aprendiz.py`** (Fase 2) — de onde sai o evento "gravei uma
  assinatura nova", que e o gatilho da pergunta. Ele ja devolve o tri-estado do
  `gravar`, e so `criado` deve perguntar.
- **`l2scanner/comandos.py`** — `Comando`, `COMANDOS_DE_MEMBRO` (o batismo fica
  FORA dele: decisao 2 do ROADMAP, nome errado e corrupcao duravel num acervo
  que nunca e podado, mesma familia de `/corrigir` e `/pegou`), `_VOCABULARIO`,
  `_AJUDA` e o tripwire.
- **`l2scanner/__main__.py`, `atender_comandos`** — o despachante, com a flag
  `avisar_o_grupo` que precisa ser ATRIBUIDA em todo ramo novo (ha portao AST
  desde o quick da janela).

### O estado de campo que esta fase encontra pronto

Medido em 31/08/2026, no acervo real do usuario: DUAS entradas anonimas ja
gravadas pela Fase 2, esperando nome.

  - `15caecfa...` — 161 pixels de texto; melhor correlacao contra um calibrado
    e 0.4247 (Mostarda)
  - `f19e3c92...` — 79 pixels de texto; melhor correlacao 0.3497 (Titander)

Os quatro calibrados sao Mostarda, Titander, Pirulito e Welazkez. A party na
tela mostra Titander e Pirulito reconhecidos e duas linhas como "Membro N".
Ou seja: duas pessoas trocaram, a Fase 2 aprendeu as duas sozinha, e o que
falta e exatamente esta fase. Isto nao e cenario de teste — e o estado do
disco do usuario agora, e o criterio de aceite mais honesto que a fase tem.

### Established Patterns

- **Tempo por parametro**; portao AST em `tests/test_presenca.py` — se nascer
  modulo novo, ele entra na tupla `MODULOS`.
- **Portugues SEM acento**; SEM travessao em texto que vai para WhatsApp ou
  console (cp1252).
- **Docstring explica POR QUE, com medida.**
- **Marcador em disco E a decisao**, nunca uma checagem anterior.

### Integration Points

- `l2scanner/acervo.py` — a escrita do nome e o marcador de pergunta
- `l2scanner/aprendiz.py` — o gatilho
- `l2scanner/comandos.py` — o comando novo e a fronteira de autorizacao
- `l2scanner/__main__.py` — o despachante e a lista viva de assinaturas
- `tests/test_comandos.py` — o tripwire do `_AJUDA`

</code_context>

<specifics>
## Specific Ideas

- A pergunta sai para o GRUPO ou so para o dono? O batismo e comando de DONO,
  entao perguntar ao grupo convidaria uma resposta que sera recusada. Mas a
  pergunta tambem e a unica forma de o grupo saber que alguem novo entrou.
  Decidir no plano, e escrever a razao.
- O usuario roda DUAS instancias sobre a mesma pasta. Elas veem partys
  DIFERENTES (cada cliente mostra os outros membros), entao as duas vao
  aprender e as duas vao querer perguntar. O `O_EXCL` do D-04 e o que faz uma
  pergunta so.

</specifics>

<deferred>
## Deferred Ideas

- OCR propor o nome como chute a confirmar (OCRB-01, v2). Medido em 1 acerto
  em 4; util como atalho, inutil como fonte, e so faz sentido depois que o
  batismo manual existir.
- Comando para esquecer uma entrada (adiado na Fase 1, com o numero na mao).

</deferred>
