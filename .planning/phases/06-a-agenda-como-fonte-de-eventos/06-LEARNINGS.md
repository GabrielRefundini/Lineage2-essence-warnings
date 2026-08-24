---
phase: 6
phase_name: "A agenda como fonte de eventos"
project: "L2 Party Scanner"
generated: "2026-08-24"
counts:
  decisions: 8
  lessons: 4
  patterns: 4
  surprises: 2
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
---

# Phase 6 Learnings: A agenda como fonte de eventos

## Decisions

### `config.toml` novo, e não `calibration.json` nem `.env`
Os horários dos eventos passam a viver num `config.toml` na raiz, lido com
`tomllib`.

**Rationale:** `calibration.json` é **escrito** pela ferramenta de calibração —
guardar os horários lá significaria que rodar `calibrar.bat` apagaria a agenda
do usuário. O `.env` é formato plano de `CHAVE=valor`, sem estrutura para uma
lista de eventos com múltiplos horários e dias. `tomllib` é stdlib desde o 3.11
(confirmado: 3.12.10 no ambiente), então custa zero dependência.
**Source:** RESEARCH.md §1

---

### A agenda nasce pura, com o tempo entrando por parâmetro
`avisos_devidos(agora, eventos, ja_enviados)` — sem relógio próprio, sem I/O.

**Rationale:** mesma disciplina que o `rastreador.py` já aplicava. Sem ela,
testar "o aviso do TvT das 21h50 de uma quinta-feira" exigiria esperar até
quinta às 21h50, e a agenda nunca teria cobertura de verdade.
**Source:** RESEARCH.md §5

---

### Marcador por aviso com `O_CREAT | O_EXCL`, e não um JSON com lock
Cada aviso enviado vira um arquivo vazio em `.agenda/`, criado atomicamente.

**Rationale:** a combinação é atômica no Windows — entre duas instâncias
competindo, exatamente uma cria o arquivo. Não precisa de lock nem de
biblioteca, e **não tem janela de corrida entre ler e escrever**, que é o furo
de um "lê o JSON, checa, escreve o JSON". Alternativas descartadas: JSON com
`msvcrt.locking` (mais código, mais modos de falha) e lock de socket (some se o
processo morrer sujo).
**Source:** RESEARCH.md §3

---

### A chave do aviso é estruturada, nunca o texto da mensagem
`{data}_{evento}-{HHMM}_{tipo}`.

**Rationale:** o texto muda toda vez que alguém melhora a redação, e a chave não
pode mudar junto — senão um aviso já enviado volta a parecer novo e a party
recebe em dobro. Foi o motivo de descartar derivar o estado do `outbox.jsonl`,
que registra tudo mas só guarda texto.
**Source:** RESEARCH.md §3

---

### `--so-agenda` é um laço separado, não um `if` no laço principal
**Rationale:** o laço de captura é o código mais crítico do projeto e não pode
ganhar ramos que só existem para um modo. Sem frame, o corpo do laço da agenda
cabe em vinte linhas e não tem como confundir.
**Source:** RESEARCH.md §4

---

### `config.toml` ausente não é erro; presente e mal formado é erro de arranque
**Rationale:** o scanner roda sem agenda desde a v1 e precisa continuar rodando
— quem nunca criou o arquivo não pode ver o programa quebrar por causa de uma
funcionalidade que não pediu. Já um erro de digitação tem que derrubar o scanner
enquanto o usuário olha para o console; às 15h ele está AFK confiando no
silêncio.
**Source:** SUMMARY.md

---

### Erro de disco em `marcar()` devolve `True`
**Rationale:** preferir o aviso duplicado ao aviso perdido. A party ignora uma
repetição, mas não adivinha um TvT que ninguém anunciou.
**Source:** SUMMARY.md

---

### `silenciar_minutos` entra no esquema já na Fase 6, lido e ignorado
**Rationale:** a Fase 7 precisa do campo. Definir o esquema sem ele forçaria uma
migração de um arquivo que o usuário já editou à mão.
**Source:** RESEARCH.md §7

---

## Lessons

### O projeto tinha divergido da própria stack documentada
`CLAUDE.md` documenta `config.toml + calibration.json`, mas a realidade era
`.env + calibration.json` — o `config.toml` nunca existiu porque nada tinha
precisado dele até esta fase.

**Context:** a pesquisa começou verificando o que o documento afirmava, e a
verificação falhou. Sem esse passo, a fase teria sido planejada em cima de um
arquivo inexistente.
**Source:** RESEARCH.md §1

---

### AGEN-06 e AGEN-07 eram o mesmo problema com o mesmo remédio
Sobreviver ao restart e não duplicar entre as duas instâncias do usuário pedem a
mesma coisa: um registro durável fora do processo.

**Context:** foram escritos como requisitos separados. Resolver um sem o outro
deixaria metade do bug em pé — e como o usuário roda duas instâncias lado a
lado, a metade que sobrasse apareceria no primeiro dia.
**Source:** SUMMARY.md

---

### O dia da semana vale para o EVENTO, nunca para o aviso
Um evento a 00:05 de segunda avisa às 23:55 de **domingo**.

**Context:** checar o dia do aviso faria esse evento nunca ser anunciado. Pelo
mesmo motivo, ontem e amanhã precisam entrar na varredura — varrer só "hoje"
perderia toda virada de dia.
**Source:** SUMMARY.md

---

### Um aviso vencido não pode ressuscitar
Só dispara até 5 minutos depois do alvo.

**Context:** subir o scanner às 16h não pode soltar o lembrete das 15h. A party
receberia um aviso de um TvT que já acabou — pior do que não avisar, porque
destrói a confiança no que o scanner diz.
**Source:** SUMMARY.md

---

## Patterns

### Tempo por parâmetro em toda camada que decide
Nenhuma camada de decisão chama `datetime.now()` por dentro; o instante entra
como argumento.

**When to use:** sempre que a lógica dependa de tempo. É o que permite testar
sete dias da semana, a virada de meia-noite e um dia inteiro minuto a minuto em
milissegundos. O `rastreador.py` já usava; a agenda herdou.
**Source:** RESEARCH.md §5, SUMMARY.md

---

### Teste de concorrência com threads, não chamadas em sequência
Para a garantia de "exatamente um envia", 16 threads largam ao mesmo tempo na
mesma chave.

**When to use:** sempre que a garantia for de exclusão mútua. Um registro com
janela de corrida entre ler e escrever **passa** no teste sequencial e falha
neste — então o teste sequencial não prova nada.
**Source:** SUMMARY.md

---

### Varredura minuto a minuto como oráculo
Percorrer um dia inteiro (1440 iterações) e afirmar a sequência exata de saídas.

**When to use:** quando o comportamento é uma função do tempo com muitos pontos
de disparo. Pega ordem, horário e ausência de duplicata numa asserção só — e é
barato justamente porque o tempo entra por parâmetro.
**Source:** SUMMARY.md

---

### Reservar no esquema o campo que a próxima fase vai usar
**When to use:** quando um arquivo é editado à mão pelo usuário e uma fase
futura vai precisar de um campo novo. Ler-e-ignorar custa nada e evita pedir
para ele editar duas vezes.
**Source:** RESEARCH.md §7

---

## Surprises

### O arquivo de configuração documentado não existia
A stack documentada em `CLAUDE.md` prometia `config.toml`; o repositório não
tinha nenhum.

**Impact:** mudou o plano da Tarefa 1 — o que parecia "ler um arquivo" virou
"introduzir um arquivo, um leitor e uma validação de arranque". Também revelou
que a documentação de stack do projeto descreve intenção, não estado.
**Source:** RESEARCH.md §1

---

### O laço principal exigia uma fonte de frames em todos os três caminhos
`--replay`, `--janela` e `mss` todos constroem uma fonte antes do laço. Não
existia caminho que rodasse sem capturar.

**Impact:** AGEN-05 ("funciona com o jogo fechado") deixou de ser uma flag e
virou um laço próprio.
**Source:** RESEARCH.md §4
